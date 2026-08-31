import {beforeEach, expect, it} from 'vitest';
import {env} from 'cloudflare:workers';
import {ScoreRepository} from '../src/repository';

let repository: ScoreRepository;

beforeEach(() => {
  repository = new ScoreRepository(env.DB);
});

it('retains only a strictly higher score for the same normalized nickname', async () => {
  await repository.submit('classic', 'Ada', 40, '2026-08-28T10:00:00Z');
  await repository.submit('classic', 'ADA', 39, '2026-08-28T11:00:00Z');
  await repository.submit('classic', 'Ada', 52, '2026-08-28T12:00:00Z');

  expect(await repository.list('classic')).toEqual([
    {nickname: 'Ada', score: 52, achieved_at: '2026-08-28T12:00:00Z', rank: 1},
  ]);
});

it('returns the retained score and its current one-based rank', async () => {
  await repository.submit('classic', 'Ada', 73, '2026-08-28T10:00:00Z');
  const result = await repository.submit('classic', 'Bob', 89, '2026-08-28T11:00:00Z');

  expect(result).toEqual({
    nickname: 'Bob',
    score: 89,
    achieved_at: '2026-08-28T11:00:00Z',
    rank: 1,
  });
});

it('keeps modes separate and orders equal scores by oldest achievement', async () => {
  await repository.submit('classic', 'Bob', 50, '2026-08-28T12:00:00Z');
  await repository.submit('classic', 'Ada', 50, '2026-08-28T10:00:00Z');
  await repository.submit('constance', 'Bob', 99, '2026-08-28T09:00:00Z');

  expect(await repository.list('classic')).toEqual([
    {nickname: 'Ada', score: 50, achieved_at: '2026-08-28T10:00:00Z', rank: 1},
    {nickname: 'Bob', score: 50, achieved_at: '2026-08-28T12:00:00Z', rank: 2},
  ]);
  expect(await repository.list('constance')).toEqual([
    {nickname: 'Bob', score: 99, achieved_at: '2026-08-28T09:00:00Z', rank: 1},
  ]);
});

it('defaults to 100 records and never returns more than 100 records', async () => {
  for (let score = 0; score < 102; score += 1) {
    await repository.submit('classic', `Player ${score}`, score, '2026-08-28T10:00:00Z');
  }

  expect(await repository.list('classic', 101)).toHaveLength(100);
  expect(await repository.list('classic')).toHaveLength(100);
});

it('returns no records when the requested limit is negative', async () => {
  await repository.submit('classic', 'Ada', 73, '2026-08-28T10:00:00Z');

  expect(await repository.list('classic', -1)).toEqual([]);
});
