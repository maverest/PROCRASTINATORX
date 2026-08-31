import {normalizeNickname} from './normalize';

export type ScoreMode = 'classic' | 'constance';

export interface ScoreRecord {
  nickname: string;
  score: number;
  achieved_at: string;
  rank: number;
}

interface StoredScore {
  nickname_key: string;
  nickname: string;
  score: number;
  achieved_at: string;
}

const MAX_LIST_SIZE = 100;

function assertMode(mode: string): asserts mode is ScoreMode {
  if (mode !== 'classic' && mode !== 'constance') {
    throw new TypeError('Unsupported score mode');
  }
}

export class ScoreRepository {
  constructor(private readonly database: D1Database) {}

  async list(mode: ScoreMode, limit = MAX_LIST_SIZE): Promise<ScoreRecord[]> {
    assertMode(mode);
    const safeLimit = Math.min(limit, MAX_LIST_SIZE);
    const {results} = await this.database
      .prepare(`
        SELECT nickname, score, achieved_at
        FROM leaderboard_scores
        WHERE mode = ?1
        ORDER BY score DESC, achieved_at ASC, nickname_key ASC
        LIMIT ?2
      `)
      .bind(mode, safeLimit)
      .all<Omit<StoredScore, 'nickname_key'>>();

    return results.map((record, index) => ({...record, rank: index + 1}));
  }

  async submit(
    mode: ScoreMode,
    nickname: string,
    score: number,
    achievedAt: string,
  ): Promise<ScoreRecord> {
    assertMode(mode);
    const normalized = normalizeNickname(nickname);

    await this.database
      .prepare(`
        INSERT INTO leaderboard_scores(mode, nickname_key, nickname, score, achieved_at)
        VALUES (?1, ?2, ?3, ?4, ?5)
        ON CONFLICT(mode, nickname_key) DO UPDATE SET
          nickname = excluded.nickname,
          score = excluded.score,
          achieved_at = excluded.achieved_at
        WHERE excluded.score > leaderboard_scores.score
      `)
      .bind(mode, normalized.key, normalized.display, score, achievedAt)
      .run();

    const retained = await this.database
      .prepare(`
        SELECT nickname_key, nickname, score, achieved_at
        FROM leaderboard_scores
        WHERE mode = ?1 AND nickname_key = ?2
      `)
      .bind(mode, normalized.key)
      .first<StoredScore>();

    if (retained === null) {
      throw new Error('Submitted score was not retained');
    }

    const ahead = await this.database
      .prepare(`
        SELECT COUNT(*) AS count
        FROM leaderboard_scores
        WHERE mode = ?1
          AND (
            score > ?2
            OR (score = ?2 AND achieved_at < ?3)
            OR (score = ?2 AND achieved_at = ?3 AND nickname_key < ?4)
          )
      `)
      .bind(mode, retained.score, retained.achieved_at, retained.nickname_key)
      .first<{count: number}>();

    return {
      nickname: retained.nickname,
      score: retained.score,
      achieved_at: retained.achieved_at,
      rank: Number(ahead?.count ?? 0) + 1,
    };
  }
}
