export class InputError extends Error {}

export function normalizeNickname(value: unknown): {key: string; display: string} {
  if (typeof value !== 'string') {
    throw new InputError('Nickname must be a string');
  }

  const display = value.normalize('NFKC').trim();
  if (/\p{Cc}/u.test(display) || [...display].length < 1 || [...display].length > 24) {
    throw new InputError('Nickname must contain between 1 and 24 visible characters');
  }

  return {key: display.toLocaleLowerCase('fr-FR'), display};
}
