export const TIMEZONES = [
  { value: 'Europe/London', key: 'london' },
  { value: 'Europe/Lisbon', key: 'lisbon' },
  { value: 'Europe/Madrid', key: 'madrid' },
  { value: 'Europe/Paris', key: 'paris' },
  { value: 'Europe/Berlin', key: 'berlin' },
  { value: 'Europe/Rome', key: 'rome' },
  { value: 'Europe/Amsterdam', key: 'amsterdam' },
  { value: 'Europe/Brussels', key: 'brussels' },
  { value: 'Europe/Vienna', key: 'vienna' },
  { value: 'Europe/Prague', key: 'prague' },
  { value: 'Europe/Warsaw', key: 'warsaw' },
  { value: 'Europe/Belgrade', key: 'belgrade' },
  { value: 'Europe/Athens', key: 'athens' },
  { value: 'Europe/Bucharest', key: 'bucharest' },
  { value: 'Europe/Helsinki', key: 'helsinki' },
  { value: 'Europe/Riga', key: 'riga' },
  { value: 'Europe/Vilnius', key: 'vilnius' },
  { value: 'Europe/Tallinn', key: 'tallinn' },
  { value: 'Asia/Jerusalem', key: 'jerusalem' },
  { value: 'Europe/Kaliningrad', key: 'kaliningrad' },
  { value: 'Europe/Moscow', key: 'moscow' },
  { value: 'Europe/Minsk', key: 'minsk' },
  { value: 'Europe/Kiev', key: 'kiev' },
  { value: 'Europe/Istanbul', key: 'istanbul' },
  { value: 'Asia/Yekaterinburg', key: 'yekaterinburg' },
  { value: 'Asia/Almaty', key: 'almaty' },
  { value: 'Asia/Novosibirsk', key: 'novosibirsk' },
  { value: 'Asia/Krasnoyarsk', key: 'krasnoyarsk' },
  { value: 'Asia/Irkutsk', key: 'irkutsk' },
  { value: 'Asia/Vladivostok', key: 'vladivostok' },
  { value: 'Asia/Kamchatka', key: 'kamchatka' },
];

export const CURRENCIES = ['RUB', 'EUR', 'ILS', 'UAH', 'BYN', 'KZT', 'USD', 'TRY', 'GEL', 'UZS'];
export const WORK_MODES = ['home', 'travel'];
export const LANG_OPTIONS = ['ru', 'en'];

export const DEFAULT_TIMEZONE = 'Europe/Moscow';
export const DEFAULT_CURRENCY = 'RUB';
export const CURRENCY_SYMBOLS = Object.freeze({
  RUB: '₽',
  EUR: '€',
  ILS: '₪',
  UAH: '₴',
  BYN: 'Br',
  KZT: '₸',
  USD: '$',
  TRY: '₺',
  GEL: '₾',
  UZS: "so'm",
});

export function getCurrencySymbol(code) {
  const normalized = String(code || '').toUpperCase();
  return CURRENCY_SYMBOLS[normalized] || normalized || '';
}

export function resolveInitialTimezone() {
  const browserTz = Intl.DateTimeFormat?.().resolvedOptions?.().timeZone;
  if (TIMEZONES.some((item) => item.value === browserTz)) {
    return browserTz;
  }
  return DEFAULT_TIMEZONE;
}
