-- Subscription and referrals

ALTER TABLE masters ADD COLUMN subscription_until TIMESTAMP;
ALTER TABLE masters ADD COLUMN trial_used BOOLEAN DEFAULT FALSE;
ALTER TABLE masters ADD COLUMN referral_code TEXT;
ALTER TABLE masters ADD COLUMN referred_by INTEGER REFERENCES masters(id);
ALTER TABLE masters ADD COLUMN reminder_sent_at TIMESTAMP;

CREATE TABLE IF NOT EXISTS star_payments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    master_id           INTEGER NOT NULL REFERENCES masters(id),
    telegram_charge_id  TEXT UNIQUE,
    payload             TEXT NOT NULL,
    stars_amount        INTEGER,
    days_added          INTEGER NOT NULL,
    subscription_until  TIMESTAMP NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS referral_bonuses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id         INTEGER NOT NULL REFERENCES masters(id),
    referee_id          INTEGER NOT NULL REFERENCES masters(id),
    bonus_on_signup     BOOLEAN DEFAULT FALSE,
    bonus_on_payment    BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(referrer_id, referee_id)
);

CREATE INDEX IF NOT EXISTS idx_star_payments_master_created
    ON star_payments(master_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_referral_bonuses_referrer
    ON referral_bonuses(referrer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_referral_bonuses_referee
    ON referral_bonuses(referee_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_masters_subscription_until
    ON masters(subscription_until);
CREATE UNIQUE INDEX IF NOT EXISTS idx_masters_referral_code_unique
    ON masters(referral_code);
