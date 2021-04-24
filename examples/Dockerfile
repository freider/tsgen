FROM python:3.9-slim AS api_server
#  Set up flask project and build typescript client code
COPY pyproject.toml /src/
COPY tsgen /src/tsgen
RUN pip install /src/

COPY examples/api.py /flask-root/
ENV FLASK_APP=/flask-root/api.py
ENV FLASK_HOST=0.0.0.0
ENV FLASK_ENV=development
RUN flask tsgen build /flask-root/frontend/generated
EXPOSE 5000
CMD ["flask", "run", "--host", "0.0.0.0"]

FROM node:15-slim AS frontend
#  build/serve static html/js bundle
WORKDIR /node-root/
COPY examples/frontend/package.json .
RUN npm install
COPY examples/frontend ./
COPY --from=api_server /flask-root/frontend/generated ./generated
RUN npx tsc --noEmit  #  type check
ENV EXAMPLE_API_ENDPOINT="api:5000"
CMD ["npx", "parcel", "src/index.html"]
