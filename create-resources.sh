echo "Create admin"
aws \
 --endpoint-url http://localhost:4593 \
 iam create-role \
 --role-name admin-role \
 --path / \
 --assume-role-policy-document file:./admin-policy.json

echo "Make s3 bucket"
aws \
  s3 mb s3://tfstate-vsnandy \
  --endpoint-url http://localhost:4566

echo "Copy the lambda function to the s3 bucket"
aws \
 s3 cp ./build/lambda.zip s3://tfstate-vsnandy/my_lambda \
 --endpoint-url http://localhost:4566

echo "Create the lambda vsnandy-lambda"
aws \
 lambda create-function \
 --endpoint-url http://localhost:4574 \
 --function-name vsnandy-lambda-api \
 --role arnd:aws:iam::000000000000:role/admin-role \
 --code S3Bucket=vsnandy-lambda,S3Key=builds/lambda.zip \
 --handler handler.handler \
 --runtime python3.8 \
 --description "Lambda handler for testing DynamoDB connector" \
 --timeout 300 \
 --memory-size 128 \

 echo "All resources initialized!"