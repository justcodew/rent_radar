"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-04
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 扩展
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("phone", sa.String(20), unique=True, nullable=True),
        sa.Column("email", sa.String(100), unique=True, nullable=True),
        sa.Column("nickname", sa.String(50), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_phone", "users", ["phone"])

    # profiles
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("city", sa.String(50), nullable=False, server_default="北京"),
        sa.Column("budget_min", sa.Integer, server_default="0"),
        sa.Column("budget_max", sa.Integer, server_default="10000"),
        sa.Column("occupants", sa.Integer, server_default="1"),
        sa.Column("move_in", sa.String(20)),
        sa.Column("areas", postgresql.JSONB, server_default="[]"),
        sa.Column("layouts", postgresql.JSONB, server_default="[]"),
        sa.Column("rent_type", sa.String(20)),
        sa.Column("size_range", postgresql.JSONB, server_default="[0,100]"),
        sa.Column("commute", postgresql.JSONB, server_default="[]"),
        sa.Column("environment", postgresql.JSONB, server_default="{}"),
        sa.Column("keywords", postgresql.JSONB, server_default="{}"),
        sa.Column("preferences", postgresql.JSONB, server_default="{}"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"])

    # listings
    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("poster_id", sa.String(100)),
        sa.Column("poster_name", sa.String(100)),
        sa.Column("title", sa.Text),
        sa.Column("content", sa.Text, server_default=""),
        sa.Column("price", sa.Integer),
        sa.Column("price_unit", sa.String(20), server_default="元/月"),
        sa.Column("area_name", sa.String(100)),
        sa.Column("location_detail", sa.Text),
        sa.Column("layout", sa.String(50)),
        sa.Column("size_sqm", sa.Integer),
        sa.Column("floor_info", sa.String(50)),
        sa.Column("orientation", sa.String(20)),
        sa.Column("contact_info", postgresql.JSONB, server_default="{}"),
        sa.Column("raw_data", postgresql.JSONB, server_default="{}"),
        sa.Column("image_urls", postgresql.JSONB, server_default="[]"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source", "source_id", name="uq_listings_source"),
    )
    op.create_index("ix_listings_source", "listings", ["source"])
    op.create_index("ix_listings_poster_id", "listings", ["poster_id"])
    op.create_index("ix_listings_price", "listings", ["price"])
    op.create_index("ix_listings_area_name", "listings", ["area_name"])
    op.create_index("ix_listings_status", "listings", ["status"])
    op.create_index("ix_listings_posted_at", "listings", ["posted_at"])

    # 全文检索 tsvector 列 + GIN 索引
    op.execute("""
        ALTER TABLE listings
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(content,''))
        ) STORED;
    """)
    op.execute("CREATE INDEX idx_listings_search_vector ON listings USING GIN(search_vector)")

    # listing_images
    op.create_table(
        "listing_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("phash", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_listing_images_listing_id", "listing_images", ["listing_id"])
    op.create_index("ix_listing_images_phash", "listing_images", ["phash"])

    # listing_scores
    op.create_table(
        "listing_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("general_score", sa.Integer, nullable=False),
        sa.Column("poster_score", sa.Integer, server_default="0"),
        sa.Column("poster_frequency_score", sa.Integer, server_default="0"),
        sa.Column("poster_age_score", sa.Integer, server_default="0"),
        sa.Column("poster_diversity_score", sa.Integer, server_default="0"),
        sa.Column("poster_contact_reuse_score", sa.Integer, server_default="0"),
        sa.Column("listing_score", sa.Integer, server_default="0"),
        sa.Column("image_authenticity_score", sa.Integer, server_default="0"),
        sa.Column("description_score", sa.Integer, server_default="0"),
        sa.Column("price_reasonable_score", sa.Integer, server_default="0"),
        sa.Column("info_completeness_score", sa.Integer, server_default="0"),
        sa.Column("risk_tags", postgresql.JSONB, server_default="[]"),
        sa.Column("evidence", postgresql.JSONB, server_default="{}"),
        sa.Column("ai_evidence", postgresql.JSONB),
        sa.Column("score_version", sa.String(20), server_default="rule-v1"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scores_general", "listing_scores", ["general_score"])
    op.create_index("ix_scores_risk_tags", "listing_scores", ["risk_tags"], postgresql_using="gin")

    # match_scores
    op.create_table(
        "match_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_score", sa.Integer, nullable=False),
        sa.Column("personalized_score", sa.Integer, nullable=False),
        sa.Column("price_match", sa.Integer, server_default="0"),
        sa.Column("commute_match", sa.Integer, server_default="0"),
        sa.Column("area_match", sa.Integer, server_default="0"),
        sa.Column("layout_match", sa.Integer, server_default="0"),
        sa.Column("environment_match", sa.Integer, server_default="0"),
        sa.Column("keyword_match", sa.Integer, server_default="0"),
        sa.Column("evidence", postgresql.JSONB, server_default="{}"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("listing_id", "profile_id", name="uq_match"),
    )
    op.create_index("ix_match_profile", "match_scores", ["profile_id"])
    op.create_index("ix_match_personalized", "match_scores", ["personalized_score"])

    # favorites / ignores / user_marks
    op.create_table(
        "favorites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(20), server_default="待看"),
        sa.Column("note", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "listing_id", name="uq_favorite"),
    )
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])

    op.create_table(
        "ignores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "listing_id", name="uq_ignore"),
    )

    op.create_table(
        "user_marks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mark_type", sa.String(50), nullable=False),
        sa.Column("note", sa.String(500)),
        sa.Column("extra", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_marks_listing", "user_marks", ["listing_id"])
    op.create_index("ix_marks_type", "user_marks", ["mark_type"])

    # tasks / notifications
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("push_threshold", sa.Integer, server_default="75"),
        sa.Column("push_frequency", sa.String(20), server_default="realtime"),
        sa.Column("push_method", sa.String(20), server_default="webpush"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL")),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.String(2000)),
        sa.Column("is_read", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_read", "notifications", ["user_id", "is_read"])

    # area_price_stats
    op.create_table(
        "area_price_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("city", sa.String(50), nullable=False),
        sa.Column("area_name", sa.String(100), nullable=False),
        sa.Column("layout", sa.String(50), nullable=False),
        sa.Column("avg_price", sa.Integer, nullable=False),
        sa.Column("sample_count", sa.Integer, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_area_price_city_area", "area_price_stats", ["city", "area_name"])


def downgrade() -> None:
    for table in [
        "area_price_stats", "notifications", "tasks",
        "user_marks", "ignores", "favorites",
        "match_scores", "listing_scores",
        "listing_images", "listings",
        "profiles", "users",
    ]:
        op.drop_table(table)
    op.execute("DROP INDEX IF EXISTS idx_listings_search_vector")
