import {expect, it} from 'vitest';
import {exports} from 'cloudflare:workers';

const worker = exports.default;

function requestScore(body: unknown, contentType = 'application/json'): Request {
  return new Request('https://leaderboard.test/scores', {
    method: 'POST',
    headers: {'content-type': contentType},
    body: JSON.stringify(body),
  });
}

it('rejects unsupported modes and malformed score submissions', async () => {
  const invalidBodies = [
    {mode: 'custom', nickname: 'Ada', score: 12},
    {mode: 'classic', nickname: '', score: 12},
    {mode: 'classic', nickname: 'Ada', score: 12.5},
    {mode: 'classic', nickname: 'Ada', score: -1},
    {mode: 'classic', nickname: 'Ada', score: 10_000},
    ['classic', 'Ada', 12],
  ];

  for (const body of invalidBodies) {
    const response = await worker.fetch(requestScore(body));
    expect(response.status).toBe(400);
    expect(response.headers.get('content-type')).toBe('application/json; charset=utf-8');
  }
});

it('rejects non-JSON score submissions', async () => {
  const response = await worker.fetch(requestScore({mode: 'classic', nickname: 'Ada', score: 12}, 'text/plain'));

  expect(response.status).toBe(400);
  expect(response.headers.get('content-type')).toBe('application/json; charset=utf-8');
});

it('submits and lists a classic record', async () => {
  const submitted = await worker.fetch(requestScore({mode: 'classic', nickname: 'Ada', score: 73}));

  expect(submitted.status).toBe(200);
  expect(submitted.headers.get('content-type')).toBe('application/json; charset=utf-8');
  expect(await submitted.json()).toMatchObject({nickname: 'Ada', score: 73, rank: 1});

  const listed = await worker.fetch(new Request('https://leaderboard.test/leaderboards/classic'));
  expect(listed.status).toBe(200);
  expect(listed.headers.get('content-type')).toBe('application/json; charset=utf-8');
  expect(await listed.json()).toEqual({
    scores: [expect.objectContaining({nickname: 'Ada', score: 73, rank: 1})],
  });
});

it('serves the constance leaderboard separately', async () => {
  await worker.fetch(requestScore({mode: 'constance', nickname: 'Ada', score: 91}));

  const classic = await worker.fetch(new Request('https://leaderboard.test/leaderboards/classic'));
  const constance = await worker.fetch(new Request('https://leaderboard.test/leaderboards/constance'));

  expect(await classic.json()).toEqual({scores: []});
  expect(await constance.json()).toEqual({
    scores: [expect.objectContaining({nickname: 'Ada', score: 91, rank: 1})],
  });
});

it('returns JSON 404 and 405 responses for unknown routes and methods', async () => {
  const notFound = await worker.fetch(new Request('https://leaderboard.test/unknown'));
  const wrongScoreMethod = await worker.fetch(new Request('https://leaderboard.test/scores'));
  const wrongLeaderboardMethod = await worker.fetch(new Request('https://leaderboard.test/leaderboards/classic', {method: 'POST'}));

  for (const response of [notFound, wrongScoreMethod, wrongLeaderboardMethod]) {
    expect(response.headers.get('content-type')).toBe('application/json; charset=utf-8');
  }
  expect(notFound.status).toBe(404);
  expect(wrongScoreMethod.status).toBe(405);
  expect(wrongLeaderboardMethod.status).toBe(405);
});
