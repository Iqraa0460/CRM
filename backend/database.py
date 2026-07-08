import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crm.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Many-to-many association tables
interaction_material = Table(
    "interaction_material",
    Base.metadata,
    Column("interaction_id", Integer, ForeignKey("interactions.id", ondelete="CASCADE"), primary_key=True),
    Column("material_id", Integer, ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True),
)

class InteractionSample(Base):
    __tablename__ = "interaction_samples"
    interaction_id = Column(Integer, ForeignKey("interactions.id", ondelete="CASCADE"), primary_key=True)
    sample_id = Column(Integer, ForeignKey("samples.id", ondelete="CASCADE"), primary_key=True)
    quantity = Column(Integer, default=1)
    
    # Relationships
    sample = relationship("Sample")

# Core Models
class HCP(Base):
    __tablename__ = "hcps"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)
    clinic = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)

class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False) # PDF, Brochure, Slide Deck

class Sample(Base):
    __tablename__ = "samples"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    stock = Column(Integer, default=0)

class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id", ondelete="SET NULL"), nullable=True)
    type = Column(String, default="Meeting") # Meeting, Call, Email, presentation
    date = Column(String, nullable=False) # YYYY-MM-DD
    time = Column(String, nullable=False) # HH:MM
    attendees = Column(String, nullable=True) # Comma-separated list or JSON
    topics_discussed = Column(String, nullable=True)
    outcomes = Column(String, nullable=True)
    follow_up_actions = Column(String, nullable=True)
    observed_sentiment = Column(String, default="Neutral") # Positive, Neutral, Negative
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    hcp = relationship("HCP")
    materials = relationship("Material", secondary=interaction_material)
    samples = relationship("InteractionSample", cascade="all, delete-orphan")
    suggested_followups = relationship("SuggestedFollowUp", back_populates="interaction", cascade="all, delete-orphan")

class SuggestedFollowUp(Base):
    __tablename__ = "suggested_followups"
    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id", ondelete="CASCADE"), nullable=False)
    suggestion_text = Column(String, nullable=False)

    interaction = relationship("Interaction", back_populates="suggested_followups")

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if database has already been seeded
        if db.query(HCP).count() == 0:
            # Seed HCPs
            hcps = [
                HCP(name="Dr. Anita Sharma", specialty="Oncology", clinic="Metro Cancer Institute", email="anita.sharma@metro.com", phone="+1-555-0190"),
                HCP(name="Dr. Vikram Patel", specialty="Cardiology", clinic="Heart Health Center", email="v.patel@hearthealth.org", phone="+1-555-0143"),
                HCP(name="Dr. Sarah Jenkins", specialty="Neurology", clinic="Brain & Spine Clinic", email="sjenkins@brainspine.net", phone="+1-555-0121"),
                HCP(name="Dr. David Kim", specialty="Endocrinology", clinic="Diabetes Care Clinic", email="dkim@diabetescare.com", phone="+1-555-0177"),
            ]
            db.add_all(hcps)
            
            # Seed Materials
            materials = [
                Material(name="OncoBoost Phase III PDF", type="PDF"),
                Material(name="OncoBoost Brochure", type="Brochure"),
                Material(name="CardiaShield Efficacy Slides", type="Slide Deck"),
                Material(name="NeuroFlow Product Sheet", type="PDF"),
            ]
            db.add_all(materials)
            
            # Seed Samples
            samples = [
                Sample(name="OncoBoost 10mg Starter Kit", stock=50),
                Sample(name="CardiaShield 5mg Trial Packs", stock=100),
                Sample(name="NeuroFlow 20mg Samples", stock=30),
            ]
            db.add_all(samples)
            db.commit()
            print("Database initialized and seeded successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
