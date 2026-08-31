import {applyD1Migrations, reset, type D1Migration} from 'cloudflare:test';
import {env} from 'cloudflare:workers';
import {beforeEach} from 'vitest';

declare global {
  namespace Cloudflare {
    interface Env {
      DB: D1Database;
      TEST_MIGRATIONS: D1Migration[];
    }

    interface GlobalProps {
      mainModule: typeof import('../src/index');
    }
  }
}

beforeEach(async () => {
  await reset();
  await applyD1Migrations(env.DB, env.TEST_MIGRATIONS);
});
