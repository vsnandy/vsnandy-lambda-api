FROM python as lambda

ARG PORT=8000
ENV PORT=$PORT
WORKDIR /usr/src
COPY . .
# Install zip in container
RUN apt-get update
RUN apt-get install zip
# Enter the src directory, install dependencies, and zip the src directory in the container
RUN pwd && ls
RUN pip freeze > requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && zip -r lambda.zip .

FROM localstack/localstack
# Copy lambda.zip into the localstack directory
COPY --from=lambda /usr/src/lambda.zip build/lambda.zip