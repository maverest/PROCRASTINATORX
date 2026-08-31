import {describe, expect, it} from 'vitest';
import {InputError, normalizeNickname} from '../src/normalize';

describe('normalizeNickname', () => {
  it('normalizes equivalent nicknames', () => {
    expect(normalizeNickname('  Ada  ')).toEqual({key: 'ada', display: 'Ada'});
    expect(normalizeNickname('Ａｄａ')).toEqual({key: 'ada', display: 'Ada'});
  });

  it.each(['', ' '.repeat(4), 'a'.repeat(25), 'A\u0000B', 42])(
    'rejects invalid nickname %j',
    value => expect(() => normalizeNickname(value)).toThrow(InputError),
  );

  it('accepts exactly 24 Unicode code points', () => {
    expect(normalizeNickname('é'.repeat(24))).toEqual({
      key: 'é'.repeat(24),
      display: 'é'.repeat(24),
    });
  });
});
