require('dotenv').config();

const { loadConfig } = require('./config');
const { buildServer } = require('./server');

async function main() {
  const config = loadConfig();
  const app = buildServer({ config });

  await app.listen({ host: config.host, port: config.port });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

