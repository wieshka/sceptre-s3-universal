# README

## Overview

This Sceptre Hook allows you to upload either files or folders to the same S3 bucket, which Sceptre is using as template_bucket_name. 

## Installation

Installation instructions

To install from the git repo
```shell
pip install git+https://github.com/wieshka/sceptre-s3-universal.git
```

## Usage/Examples

Use the hook with a [hook point](https://docs.sceptre-project.org/latest/docs/hooks.html#hook-points)

```yaml
hooks:
  hook_point:
    - !upload
         path: <relative-path>
         name: <reference name>

```

## Example

config/stack.yaml
```yaml
hooks:
  before_create:
    - !upload
      path: ./src/lambdas/cloudformation-macros
      name: cloudformationmacros
```
templates/stack.yaml
```yaml
  CloudFormationMacrosLambda:
    Type: AWS::Lambda::Function
    Properties:
      Runtime: python3.11
      Timeout: 120
      Handler: lambda.handler
      Role: !GetAtt PermissionsRole.Arn
      Code:
        S3Bucket: {{ sceptre_user_data.template_bucket_name }}
        S3Key: {{ sceptre_user_data.cloudformationmacros }}
      Layers:
        - !Ref CommonLayer
```


## Credit
Heavily re-used code from https://github.com/henrist/sceptre-s3-packager, in fact, entire Hook package is significantly inspired by it, with goal to work with latest Sceptre & Python versions. Long time user myself of sceptre-s3-packager.