export type { Locale, Messages } from "./types";
export { zh } from "./zh";
export { en } from "./en";

import type { Locale } from "./types";
import { en } from "./en";
import { zh } from "./zh";

const table = { zh, en } as const;

export function getMessages(locale: Locale) {
  return table[locale];
}
