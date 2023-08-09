# -*- coding: utf-8 -*-

from sceptre.hooks import Hook
from sceptre.exceptions import SceptreException
import os
import zipfile
import hashlib

try:
    from StringIO import StringIO as BufferIO
except ImportError:
    from io import BytesIO as BufferIO

try:
    import zlib  # noqa: F401

    compression = zipfile.ZIP_DEFLATED
except ImportError:
    compression = zipfile.ZIP_STORED


def get_s3_name(md5):
    return "sceptre/{}".format(md5.hexdigest())


class Upload(Hook):
    def run(self):
        self.logger.debug("Upload hook triggered")
        self.logger.debug(dir(self.stack))
        self.logger.debug(self.stack.template_bucket_name)

        if self.stack.template_bucket_name is None:
            self.logger.error(
                "No explicit Template bucket name has been supplied to Stack config, yet Upload hook is specified. Upload hook requires having <template_bucket_name> set. "
            )
            raise SceptreException(
                "No explicit Template bucket name has been supplied to Stack config, yet Upload hook is specified. Upload hook requires having <template_bucket_name> set. "
            )

        zip_target = self.argument["path"]
        self.logger.debug(f"Handling path: {zip_target}")
        content = HandlePath(self).get_zip_contents()

        md5 = hashlib.new("md5")
        md5.update(content)

        s3_key = get_s3_name(md5)

        self.logger.debug(
            "{} resolved to s3://{}/{}".format(
                zip_target, self.stack.template_bucket_name, s3_key
            )
        )

        try:
            response = self.stack.connection_manager.call(
                service="s3",
                command="head_object",
                kwargs={"Bucket": self.stack.template_bucket_name, "Key": s3_key},
            )
            self.logger.debug(response)
        except Exception as e:
            if e.response["Error"]["Code"] not in ["404", "412"]:
                raise e

            self.logger.debug(
                "putting {} to s3://{}/{}".format(
                    zip_target, self.stack.template_bucket_name, s3_key
                )
            )

            response = self.stack.connection_manager.call(
                service="s3",
                command="put_object",
                kwargs={
                    "Bucket": self.stack.template_bucket_name,
                    "Key": s3_key,
                    "Body": content,
                },
            )
            self.logger.debug(response)

            self.logger.debug(
                "s3://{}/{} put for {}".format(
                    self.stack.template_bucket_name, s3_key, zip_target
                )
            )
        self.stack.sceptre_user_data[self.argument["name"]] = s3_key
        self.stack.sceptre_user_data[
            "template_bucket_name"
        ] = self.stack.template_bucket_name


class HandlePath:
    def __init__(self, context):
        self.logger = context.logger
        self.zip_target = context.argument["path"]

    def get_zip_contents(self):
        if os.path.isdir(self.zip_target):
            self.logger.debug(
                "Path is directory, zipping prior uploading {}".format(self.zip_target)
            )
            return self.zip_dir_contents()
        elif os.path.isfile(self.zip_target):
            self.logger.debug(
                "Path is file, it will be uploaded as is {}".format(self.zip_target)
            )
            return self.read_file_contents()

    def zip_dir_contents(self):
        files = sorted(
            [
                os.path.relpath(os.path.join(root, file), self.zip_target)
                for root, _, files in os.walk(self.zip_target)
                for file in files
            ]
        )

        if len(files) == 0:
            raise Exception("No files found in {}".format(self.zip_target))

        buffer = BufferIO()

        with zipfile.ZipFile(buffer, mode="w", compression=compression) as zf:
            for file in files:
                real_file = os.path.join(self.zip_target, file)
                self.logger.info("zipping file {}".format(real_file))
                self.write_file_to_zip(zf, real_file, file)

        buffer.seek(0)
        return buffer.read()

    def read_file_contents(self):
        pass

    def write_file_to_zip(self, zf, filename, arcname):
        st = os.stat(filename)

        zinfo = zipfile.ZipInfo(arcname, (2018, 1, 1, 0, 0, 0))
        zinfo.external_attr = (st[0] & 0xFFFF) << 16  # Unix attributes
        zinfo.compress_type = compression

        content = self.read_file_contents(filename)

        zf.writestr(zinfo, content)

    def read_file_contents(self, filename):
        with open(filename, "rb") as fp:
            return fp.read()
