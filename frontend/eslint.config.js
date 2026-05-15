const nextConfig = require("eslint-config-next");
const nextCoreWebVitals = require("eslint-config-next/core-web-vitals");
const nextTypescript = require("eslint-config-next/typescript");

const configs = Array.isArray(nextConfig) ? nextConfig : [nextConfig];
const cwvConfigs = Array.isArray(nextCoreWebVitals) ? nextCoreWebVitals : [nextCoreWebVitals];
const tsConfigs = Array.isArray(nextTypescript) ? nextTypescript : [nextTypescript];

module.exports = [...configs, ...cwvConfigs, ...tsConfigs];
