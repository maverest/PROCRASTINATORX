import {InputError, normalizeNickname} from './normalize';
import {ScoreRepository, type ScoreMode} from './repository';

interface Env {
  DB: D1Database;
}

const JSON_HEADERS = {'content-type': 'application/json; charset=utf-8'};
const MODES = new Set<ScoreMode>(['classic', 'constance']);

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {status, headers: JSON_HEADERS});
}

function isJsonContent(request: Request): boolean {
  return request.headers.get('content-type')?.split(';', 1)[0]?.trim().toLowerCase() === 'application/json';
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseScoreSubmission(value: unknown): {mode: ScoreMode; nickname: string; score: number} | null {
  if (!isRecord(value) || !MODES.has(value.mode as ScoreMode)) {
    return null;
  }

  if (typeof value.nickname !== 'string' || typeof value.score !== 'number') {
    return null;
  }

  if (!Number.isInteger(value.score) || value.score < 0 || value.score > 9999) {
    return null;
  }

  try {
    normalizeNickname(value.nickname);
  } catch (error) {
    if (error instanceof InputError) {
      return null;
    }
    throw error;
  }

  return {mode: value.mode as ScoreMode, nickname: value.nickname, score: value.score};
}

export default {
  async fetch(request, env): Promise<Response> {
    const pathname = new URL(request.url).pathname;
    const leaderboardMode = pathname.match(/^\/leaderboards\/(classic|constance)$/)?.[1] as ScoreMode | undefined;

    if (leaderboardMode !== undefined) {
      if (request.method !== 'GET') {
        return json({error: 'Method not allowed'}, 405);
      }
      return json({scores: await new ScoreRepository(env.DB).list(leaderboardMode)});
    }

    if (pathname !== '/scores') {
      return json({error: 'Not found'}, 404);
    }

    if (request.method !== 'POST') {
      return json({error: 'Method not allowed'}, 405);
    }

    if (!isJsonContent(request)) {
      return json({error: 'Invalid JSON body'}, 400);
    }

    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return json({error: 'Invalid JSON body'}, 400);
    }

    const submission = parseScoreSubmission(body);
    if (submission === null) {
      return json({error: 'Invalid score submission'}, 400);
    }

    const record = await new ScoreRepository(env.DB).submit(
      submission.mode,
      submission.nickname,
      submission.score,
      new Date().toISOString(),
    );
    return json(record);
  },
} satisfies ExportedHandler<Env>;
