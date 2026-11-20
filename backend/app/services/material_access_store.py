from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, List, Optional

from sqlalchemy import Boolean, Float, Integer, String, Text, create_engine, select, text, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.services.ipfs_utils import normalize_cid

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "backend" / "data" / "matchain.sqlite3"


class AccessBase(DeclarativeBase):
    pass


class MaterialAccessRecord(AccessBase):
    __tablename__ = "material_access_records"

    material_hash: Mapped[str] = mapped_column(String(66), primary_key=True)
    cid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    owner_wallet: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    encryption_key_hex: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    encryption_nonce_hex: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    encryption_tag_hex: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_confidential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    public_metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cid_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    storage_provider: Mapped[str] = mapped_column(String(64), nullable=False, default="kubo")
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    gateway_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)


class MaterialValidationRecord(AccessBase):
    __tablename__ = "material_validation_records"

    material_hash: Mapped[str] = mapped_column(String(66), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, verified, rejected
    validator_wallet: Mapped[Optional[str]] = mapped_column(String(42), nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    e_hull_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    distance_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    consensus_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    report_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validated_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    staked_amount_eth: Mapped[float] = mapped_column(Float, default=0.05)


class MaterialAccessStore:
    """Persistent storage for material ownership, confidential access records,
    server-side AES encryption keys, and decentralized validator attestations.
    """

    def __init__(self, database_path: Path = DEFAULT_DATABASE_PATH) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{database_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        AccessBase.metadata.create_all(self.engine)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Applies backward-compatible column migrations for existing SQLite stores."""
        try:
            with self.engine.begin() as conn:
                existing_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(material_access_records)"))}
                new_cols = [
                    ("cid_version", "INTEGER NOT NULL DEFAULT 1"),
                    ("storage_provider", "VARCHAR(64) NOT NULL DEFAULT 'kubo'"),
                    ("is_pinned", "BOOLEAN NOT NULL DEFAULT 1"),
                    ("is_verified", "BOOLEAN NOT NULL DEFAULT 1"),
                    ("gateway_url", "VARCHAR(512)"),
                ]
                for col_name, col_def in new_cols:
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE material_access_records ADD COLUMN {col_name} {col_def}"))
        except Exception:
            pass

    def register_material(
        self,
        material_hash: str,
        cid: str,
        owner_wallet: str,
        filename: str,
        content_type: str = "application/octet-stream",
        encryption_key_hex: Optional[str] = None,
        encryption_nonce_hex: Optional[str] = None,
        encryption_tag_hex: Optional[str] = None,
        is_encrypted: bool = True,
        is_confidential: bool = True,
        size_bytes: int = 0,
        public_metadata: Optional[dict[str, Any]] = None,
        cid_version: int = 1,
        storage_provider: str = "kubo",
        is_pinned: bool = True,
        is_verified: bool = True,
        gateway_url: Optional[str] = None,
    ) -> dict[str, Any]:
        clean_owner = owner_wallet.strip().lower()
        clean_cid = normalize_cid(cid)
        now = time.time()
        metadata_str = json.dumps(public_metadata, sort_keys=True) if public_metadata else None

        with self.sessions.begin() as session:
            existing = session.get(MaterialAccessRecord, material_hash)
            if existing:
                existing.cid = clean_cid
                existing.owner_wallet = clean_owner
                existing.filename = filename
                existing.content_type = content_type
                existing.encryption_key_hex = encryption_key_hex
                existing.encryption_nonce_hex = encryption_nonce_hex
                existing.encryption_tag_hex = encryption_tag_hex
                existing.is_encrypted = is_encrypted
                existing.is_confidential = is_confidential
                existing.size_bytes = size_bytes
                existing.public_metadata_json = metadata_str
                existing.cid_version = cid_version
                existing.storage_provider = storage_provider
                existing.is_pinned = is_pinned
                existing.is_verified = is_verified
                existing.gateway_url = gateway_url
                record = existing
            else:
                record = MaterialAccessRecord(
                    material_hash=material_hash,
                    cid=clean_cid,
                    owner_wallet=clean_owner,
                    filename=filename,
                    content_type=content_type,
                    encryption_key_hex=encryption_key_hex,
                    encryption_nonce_hex=encryption_nonce_hex,
                    encryption_tag_hex=encryption_tag_hex,
                    is_encrypted=is_encrypted,
                    is_confidential=is_confidential,
                    size_bytes=size_bytes,
                    created_at=now,
                    public_metadata_json=metadata_str,
                    cid_version=cid_version,
                    storage_provider=storage_provider,
                    is_pinned=is_pinned,
                    is_verified=is_verified,
                    gateway_url=gateway_url,
                )
                session.add(record)

        return self.get_by_material_hash(material_hash) or {}

    def get_by_material_hash(self, material_hash: str) -> Optional[dict[str, Any]]:
        with self.sessions() as session:
            record = session.get(MaterialAccessRecord, material_hash)
            return self._to_dict(record) if record else None

    def get_by_cid(self, cid: str) -> Optional[dict[str, Any]]:
        clean_cid = normalize_cid(cid)

        with self.sessions() as session:
            records = session.scalars(
                select(MaterialAccessRecord).where(MaterialAccessRecord.cid == clean_cid)
            ).all()
            if records:
                return self._to_dict(records[0])
            return None

    def find_by_identifier(self, identifier: str) -> Optional[dict[str, Any]]:
        """Finds record by material_hash or CID."""
        clean = identifier.strip()
        if clean.startswith("0x") and len(clean) == 66:
            rec = self.get_by_material_hash(clean)
            if rec:
                return rec
        if len(clean) == 64 and all(c in "0123456789abcdefABCDEF" for c in clean):
            rec = self.get_by_material_hash(f"0x{clean}")
            if rec:
                return rec
        rec = self.get_by_cid(clean)
        if rec:
            return rec
        return self.get_by_material_hash(clean)

    def list_by_owner(self, owner_wallet: str) -> List[dict[str, Any]]:
        clean_owner = owner_wallet.strip().lower()
        with self.sessions() as session:
            records = session.scalars(
                select(MaterialAccessRecord)
                .where(MaterialAccessRecord.owner_wallet == clean_owner)
                .order_by(MaterialAccessRecord.created_at.desc())
            ).all()
            return [self._to_dict(r) for r in records]

    def is_owner(self, identifier: str, wallet_address: Optional[str]) -> bool:
        if not wallet_address:
            return False
        rec = self.find_by_identifier(identifier)
        if not rec:
            return False
        return rec["owner_wallet"].lower() == wallet_address.strip().lower()

    @staticmethod
    def _to_dict(record: MaterialAccessRecord) -> dict[str, Any]:
        return {
            "material_hash": record.material_hash,
            "cid": record.cid,
            "owner_wallet": record.owner_wallet,
            "filename": record.filename,
            "content_type": record.content_type,
            "encryption_key_hex": record.encryption_key_hex,
            "encryption_nonce_hex": record.encryption_nonce_hex,
            "encryption_tag_hex": record.encryption_tag_hex,
            "is_encrypted": record.is_encrypted,
            "is_confidential": record.is_confidential,
            "size_bytes": record.size_bytes,
            "created_at": record.created_at,
            "public_metadata": json.loads(record.public_metadata_json) if record.public_metadata_json else None,
            "cid_version": getattr(record, "cid_version", 1) or 1,
            "storage_provider": getattr(record, "storage_provider", "kubo") or "kubo",
            "is_pinned": bool(getattr(record, "is_pinned", False)),
            "is_verified": bool(getattr(record, "is_verified", False)),
            "gateway_url": getattr(record, "gateway_url", None),
        }

    def record_validation(
        self,
        material_hash: str,
        status: str = "verified",
        validator_wallet: Optional[str] = None,
        score: float = 0.95,
        e_hull_passed: bool = True,
        distance_passed: bool = True,
        consensus_passed: bool = True,
        report: Optional[dict[str, Any]] = None,
        staked_amount_eth: float = 0.05,
    ) -> dict[str, Any]:
        clean_validator = validator_wallet.strip().lower() if validator_wallet else None
        now = time.time()
        report_str = json.dumps(report, sort_keys=True) if report else None

        with self.sessions.begin() as session:
            existing = session.get(MaterialValidationRecord, material_hash)
            if existing:
                existing.status = status
                existing.validator_wallet = clean_validator
                existing.score = score
                existing.e_hull_passed = e_hull_passed
                existing.distance_passed = distance_passed
                existing.consensus_passed = consensus_passed
                existing.report_json = report_str
                existing.validated_at = now
                existing.staked_amount_eth = staked_amount_eth
                record = existing
            else:
                record = MaterialValidationRecord(
                    material_hash=material_hash,
                    status=status,
                    validator_wallet=clean_validator,
                    score=score,
                    e_hull_passed=e_hull_passed,
                    distance_passed=distance_passed,
                    consensus_passed=consensus_passed,
                    report_json=report_str,
                    validated_at=now,
                    staked_amount_eth=staked_amount_eth,
                )
                session.add(record)

        return self.get_validation(material_hash) or {}

    def get_validation(self, material_hash: str) -> Optional[dict[str, Any]]:
        with self.sessions() as session:
            record = session.get(MaterialValidationRecord, material_hash)
            return self._validation_to_dict(record) if record else None

    def list_validations(self) -> List[dict[str, Any]]:
        with self.sessions() as session:
            records = session.scalars(select(MaterialValidationRecord)).all()
            return [self._validation_to_dict(r) for r in records]

    @staticmethod
    def _validation_to_dict(record: MaterialValidationRecord) -> dict[str, Any]:
        return {
            "material_hash": record.material_hash,
            "status": record.status,
            "validator_wallet": record.validator_wallet,
            "score": record.score,
            "e_hull_passed": record.e_hull_passed,
            "distance_passed": record.distance_passed,
            "consensus_passed": record.consensus_passed,
            "report": json.loads(record.report_json) if record.report_json else None,
            "validated_at": record.validated_at,
            "staked_amount_eth": record.staked_amount_eth,
        }
