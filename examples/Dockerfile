FROM python:3.9-slim AS api_server
#  Set up flask project and build typescript client code
RUN pip install poetry
RUN poetry config virtualenvs.create false
WORKDIR /src
COPY pyproject.toml ./
RUN poetry install --no-root
COPY tsgen ./tsgen/
RUN poetry install

COPY examples/api.py /flask-root/
ENV FLASK_APP=/flask-root/api.py
ENV FLASK_ENV=development
ENV TSGEN_OUTPUT_DIR=/tsgen-output
RUN poetry run flask tsgen build
EXPOSE 5000
CMD ["flask", "run", "--host", "0.0.0.0"]

FROM node:15-slim AS frontend
#  build/serve static html/js bundle
WORKDIR /node-root/
COPY examples/frontend/package.json .
RUN npm install
COPY examples/frontend ./
COPY --from=api_server /tsgen-output ./generated
RUN npx tsc --noEmit  #  type check
ENV EXAMPLE_API_ENDPOINT="api:5000"
CMD ["npx", "parcel", "src/index.html"]
