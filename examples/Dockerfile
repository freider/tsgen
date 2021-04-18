FROM python:3.9-slim AS backend

COPY pyproject.toml /src/
COPY tsgen /src/tsgen
RUN pip install /src/

COPY examples/app.py /flask-root/
ENV FLASK_APP=/flask-root/app.py
RUN flask tsgen build > api.ts


FROM node:15-slim AS js
COPY examples/frontend /src
COPY --from=backend api.ts /src/
WORKDIR /src/
RUN npm install
RUN npx tsc --noEmit  #type check
RUN npx parcel build main.html  #build index.html bundle

FROM backend AS server
ENV FLASK_HOST=0.0.0.0
ENV FLASK_ENV=development

COPY --from=js /src/index.html /flask-root/static/
EXPOSE 5000
CMD ["flask", "run", "--host", "0.0.0.0"]
