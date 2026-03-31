-- ================================================================
-- PixelMind 数据库初始化脚本
-- 执行顺序：安装扩展 → 建表 → 建索引 → 建触发器 → 写入初始数据
-- ================================================================

-- ── 扩展 ──────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector，RAG 场景启用

-- ================================================================
-- 用户表
-- ================================================================
CREATE TABLE IF NOT EXISTS users (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email                VARCHAR(255) UNIQUE,
    phone                VARCHAR(20)  UNIQUE,
    password_hash        VARCHAR(255),
    oauth_wechat_openid  VARCHAR(128) UNIQUE,
    oauth_wechat_unionid VARCHAR(128),
    oauth_google_sub     VARCHAR(128) UNIQUE,
    nickname             VARCHAR(100) NOT NULL DEFAULT '用户',
    avatar_url           TEXT,
    locale               VARCHAR(10)  NOT NULL DEFAULT 'zh-CN',
    membership_level     SMALLINT     NOT NULL DEFAULT 0,
    membership_expires_at TIMESTAMPTZ,
    is_active            BOOLEAN      NOT NULL DEFAULT true,
    is_email_verified    BOOLEAN      NOT NULL DEFAULT false,
    last_login_at        TIMESTAMPTZ,
    last_login_ip        INET,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email
    ON users(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_phone
    ON users(phone) WHERE phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_wechat_openid
    ON users(oauth_wechat_openid) WHERE oauth_wechat_openid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_google_sub
    ON users(oauth_google_sub) WHERE oauth_google_sub IS NOT NULL;

-- ================================================================
-- 积分账户表
-- ================================================================
CREATE TABLE IF NOT EXISTS points_accounts (
    id             UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id        UUID    NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    balance        DECIMAL(18, 2) NOT NULL DEFAULT 0 CHECK (balance >= 0),
    frozen_balance DECIMAL(18, 2) NOT NULL DEFAULT 0 CHECK (frozen_balance >= 0),
    total_earned   DECIMAL(18, 2) NOT NULL DEFAULT 0,
    total_spent    DECIMAL(18, 2) NOT NULL DEFAULT 0,
    version        INTEGER        NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- ================================================================
-- 积分流水表
-- ================================================================
CREATE TABLE IF NOT EXISTS points_transactions (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID         NOT NULL REFERENCES users(id),
    transaction_id  VARCHAR(200) NOT NULL,
    type            VARCHAR(20)  NOT NULL,
    amount          DECIMAL(18, 2) NOT NULL,
    balance_before  DECIMAL(18, 2) NOT NULL,
    balance_after   DECIMAL(18, 2) NOT NULL,
    source          VARCHAR(50)  NOT NULL,
    reference_id    VARCHAR(200),
    reference_type  VARCHAR(50),
    remark          TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_points_transaction_id UNIQUE (transaction_id)
);

CREATE INDEX IF NOT EXISTS idx_points_tx_user_time
    ON points_transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_points_tx_ref
    ON points_transactions(reference_id) WHERE reference_id IS NOT NULL;

-- ================================================================
-- AI 生成任务表
-- ================================================================
CREATE TABLE IF NOT EXISTS generation_jobs (
    id               UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID         NOT NULL REFERENCES users(id),
    tool_slug        VARCHAR(50)  NOT NULL,
    model_provider   VARCHAR(50)  NOT NULL,
    model_name       VARCHAR(100) NOT NULL,
    prompt           TEXT         NOT NULL,
    negative_prompt  TEXT,
    aspect_ratio     VARCHAR(10)  NOT NULL DEFAULT '2:3',
    style_preset     VARCHAR(50),
    reference_image_url TEXT,
    extra_params     JSONB        DEFAULT '{}',
    status           VARCHAR(20)  NOT NULL DEFAULT 'submitted',
    celery_task_id   VARCHAR(255),
    progress         SMALLINT     NOT NULL DEFAULT 0,
    error_message    TEXT,
    credits_frozen   DECIMAL(18, 2),
    credits_charged  DECIMAL(18, 2),
    credits_refunded DECIMAL(18, 2) DEFAULT 0,
    queued_at        TIMESTAMPTZ,
    processing_started_at TIMESTAMPTZ,
    completed_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_user_status
    ON generation_jobs(user_id, status);
CREATE INDEX IF NOT EXISTS idx_jobs_user_created
    ON generation_jobs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_celery_id
    ON generation_jobs(celery_task_id) WHERE celery_task_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_jobs_status_queued
    ON generation_jobs(created_at) WHERE status = 'queued';

-- ================================================================
-- 资产表
-- ================================================================
CREATE TABLE IF NOT EXISTS assets (
    id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id       UUID        NOT NULL REFERENCES generation_jobs(id) ON DELETE CASCADE,
    user_id      UUID        NOT NULL REFERENCES users(id),
    storage_key  VARCHAR(500) NOT NULL,
    thumb_key    VARCHAR(500),
    file_format  VARCHAR(20)  NOT NULL DEFAULT 'webp',
    width        INTEGER,
    height       INTEGER,
    file_size    INTEGER,
    is_public    BOOLEAN      NOT NULL DEFAULT false,
    is_starred   BOOLEAN      NOT NULL DEFAULT false,
    likes_count  INTEGER      NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assets_user
    ON assets(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assets_user_starred
    ON assets(user_id) WHERE is_starred = true;
CREATE INDEX IF NOT EXISTS idx_assets_public
    ON assets(created_at DESC) WHERE is_public = true;
CREATE INDEX IF NOT EXISTS idx_assets_job
    ON assets(job_id);

-- ================================================================
-- 资产点赞表
-- ================================================================
CREATE TABLE IF NOT EXISTS asset_likes (
    asset_id   UUID        NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    user_id    UUID        NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (asset_id, user_id)
);

-- ================================================================
-- 会员订单表
-- ================================================================
CREATE TABLE IF NOT EXISTS membership_orders (
    id                UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID         NOT NULL REFERENCES users(id),
    plan_id           VARCHAR(50)  NOT NULL,
    plan_name         VARCHAR(100) NOT NULL,
    credits_granted   DECIMAL(18, 2) NOT NULL,
    membership_level  SMALLINT     NOT NULL,
    membership_days   INTEGER      NOT NULL,
    currency          VARCHAR(10)  NOT NULL,
    amount            DECIMAL(10, 2) NOT NULL,
    payment_provider  VARCHAR(20)  NOT NULL,
    payment_order_id  VARCHAR(255),
    payment_intent_id VARCHAR(255),
    status            VARCHAR(20)  NOT NULL DEFAULT 'pending',
    paid_at           TIMESTAMPTZ,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_user
    ON membership_orders(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_payment_id
    ON membership_orders(payment_order_id) WHERE payment_order_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_stripe_intent
    ON membership_orders(payment_intent_id) WHERE payment_intent_id IS NOT NULL;

-- ================================================================
-- 工具配置表
-- ================================================================
CREATE TABLE IF NOT EXISTS tools (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug            VARCHAR(50)  NOT NULL UNIQUE,
    name_zh         VARCHAR(100) NOT NULL,
    name_en         VARCHAR(100) NOT NULL,
    description_zh  TEXT,
    description_en  TEXT,
    icon_url        TEXT,
    credits_min     SMALLINT     NOT NULL,
    credits_max     SMALLINT     NOT NULL,
    model_config    JSONB        NOT NULL DEFAULT '{}',
    supported_aspect_ratios  TEXT[] DEFAULT ARRAY['1:1','2:3','3:4','9:16'],
    supported_style_presets  TEXT[] DEFAULT ARRAY[]::TEXT[],
    supports_reference_image BOOLEAN NOT NULL DEFAULT false,
    supports_negative_prompt BOOLEAN NOT NULL DEFAULT true,
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    sort_order      SMALLINT     NOT NULL DEFAULT 0,
    seo_title_zh    VARCHAR(200),
    seo_title_en    VARCHAR(200),
    seo_desc_zh     TEXT,
    seo_desc_en     TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ================================================================
-- Refresh Token 表
-- ================================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL UNIQUE,
    device_info TEXT,
    ip_address  INET,
    is_revoked  BOOLEAN      NOT NULL DEFAULT false,
    expires_at  TIMESTAMPTZ  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user
    ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_active
    ON refresh_tokens(user_id) WHERE is_revoked = false;

-- ================================================================
-- 通用 updated_at 自动更新触发器
-- ================================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
  CREATE TRIGGER trg_users_updated_at
      BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER trg_points_accounts_updated_at
      BEFORE UPDATE ON points_accounts FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER trg_generation_jobs_updated_at
      BEFORE UPDATE ON generation_jobs FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER trg_assets_updated_at
      BEFORE UPDATE ON assets FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER trg_membership_orders_updated_at
      BEFORE UPDATE ON membership_orders FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TRIGGER trg_tools_updated_at
      BEFORE UPDATE ON tools FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ================================================================
-- 初始工具数据（六大核心工具）
-- ================================================================
INSERT INTO tools (slug, name_zh, name_en, credits_min, credits_max, model_config,
                   supported_aspect_ratios, supported_style_presets,
                   supports_reference_image, sort_order,
                   seo_title_zh, seo_title_en)
VALUES
  ('character-art', '角色立绘', 'Character Art', 3, 5,
   '{"default":{"provider":"tongyi","model":"wanx-v1"},"membership_2":{"provider":"openai","model":"dall-e-3"},"fallback":["tongyi/wanx-v1","stability/stable-diffusion-xl"]}',
   ARRAY['2:3','3:4','1:1'],
   ARRAY['奇幻RPG','二次元','像素游戏','写实风格','赛博朋克'],
   true, 1,
   'AI角色立绘生成 - 游戏角色设计首选', 'AI Character Art Generator for Game Design'),

  ('environment-art', '场景原画', 'Environment Art', 4, 6,
   '{"default":{"provider":"tongyi","model":"wanx-v1"},"membership_2":{"provider":"openai","model":"dall-e-3"},"fallback":["tongyi/wanx-v1"]}',
   ARRAY['16:9','21:9','3:4','1:1'],
   ARRAY['奇幻RPG','二次元','像素游戏','写实风格','赛博朋克'],
   false, 2,
   'AI场景原画生成 - 游戏背景设计工具', 'AI Environment Art Generator for Games'),

  ('sprite-sheet', 'Sprite 批量', 'Sprite Sheet', 2, 2,
   '{"default":{"provider":"stability","model":"stable-diffusion-xl"},"fallback":["tongyi/wanx-v1"]}',
   ARRAY['1:1'],
   ARRAY['像素游戏','二次元'],
   false, 3,
   'AI Sprite 批量生成 - 游戏图标量产工具', 'AI Sprite Sheet Generator for Game Assets'),

  ('motion-preview', '动画预览', 'Motion Preview', 15, 25,
   '{"default":{"provider":"tongyi","model":"wanx-video-v1"},"fallback":[]}',
   ARRAY['16:9','1:1'],
   ARRAY[],
   true, 4,
   'AI动画预览生成 - 游戏动作验证工具', 'AI Motion Preview Generator for Game Animation'),

  ('texture-generator', '材质纹理', 'Texture Generator', 3, 5,
   '{"default":{"provider":"stability","model":"stable-diffusion-xl"},"fallback":["tongyi/wanx-v1"]}',
   ARRAY['1:1'],
   ARRAY['写实风格','像素游戏','赛博朋克'],
   true, 5,
   'AI材质纹理生成 - 游戏贴图升频工具', 'AI Texture Generator for Game Materials'),

  ('ai-retouch', '细节精修', 'AI Retouch', 2, 2,
   '{"default":{"provider":"stability","model":"stable-diffusion-inpainting"},"fallback":[]}',
   ARRAY['1:1','2:3','3:4'],
   ARRAY[],
   true, 6,
   'AI细节精修 - 游戏素材 Inpainting 工具', 'AI Retouch & Inpainting for Game Assets')

ON CONFLICT (slug) DO NOTHING;
