const { createProxyMiddleware } = require("http-proxy-middleware");

module.exports = function (app) {
  const envHost = process.env['EXAMPLE_API_ENDPOINT'];
  const apiHost = envHost? envHost: "localhost:5000";

  app.use(
    createProxyMiddleware("/api", {
      target: `http://${apiHost}/`,
    })
  );
};
