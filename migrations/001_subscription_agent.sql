-- 구독 에이전트 도입을 위한 PostgreSQL 스키마 변경안.
-- 이 프로젝트에는 아직 마이그레이션 도구가 없으므로 기존 개발 DB를 유지해야
-- 할 때만 수동 적용한다. 빈 DB는 SQLModel.metadata.create_all()로 생성 가능하다.

ALTER TABLE welfare_policies
    ADD COLUMN IF NOT EXISTS application_deadline DATE,
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS abolished_at TIMESTAMP;

-- 과거 적재기는 정책 청크마다 행을 만들었다. 구독 FK를 만들기 전에 같은
-- service_id 중 가장 작은 id만 남겨 정책별 한 행으로 정리한다.
DELETE FROM welfare_policies duplicated
USING welfare_policies retained
WHERE duplicated.service_id = retained.service_id
  AND duplicated.id > retained.id;

CREATE UNIQUE INDEX IF NOT EXISTS ix_welfare_policies_service_id_unique
    ON welfare_policies (service_id);

CREATE TABLE IF NOT EXISTS policy_subscriptions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    policy_id INTEGER NOT NULL REFERENCES welfare_policies(id),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    cancelled_at TIMESTAMP,
    CONSTRAINT uq_subscription_user_policy UNIQUE (user_id, policy_id)
);

CREATE INDEX IF NOT EXISTS ix_policy_subscriptions_user_id
    ON policy_subscriptions (user_id);
CREATE INDEX IF NOT EXISTS ix_policy_subscriptions_policy_id
    ON policy_subscriptions (policy_id);
CREATE INDEX IF NOT EXISTS ix_policy_subscriptions_status
    ON policy_subscriptions (status);

CREATE TABLE IF NOT EXISTS notification_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    policy_news_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    is_paused BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS subscription_dialogs (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(30) NOT NULL,
    stage VARCHAR(30) NOT NULL,
    policy_query VARCHAR(300),
    candidate_policy_ids JSON NOT NULL,
    selected_policy_id INTEGER REFERENCES welfare_policies(id),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_subscription_dialogs_conversation_id
    ON subscription_dialogs (conversation_id);
CREATE INDEX IF NOT EXISTS ix_subscription_dialogs_user_id
    ON subscription_dialogs (user_id);
CREATE INDEX IF NOT EXISTS ix_subscription_dialogs_stage
    ON subscription_dialogs (stage);
CREATE INDEX IF NOT EXISTS ix_subscription_dialogs_expires_at
    ON subscription_dialogs (expires_at);
