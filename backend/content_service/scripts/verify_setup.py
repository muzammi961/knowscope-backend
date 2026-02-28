import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)

print(f"Added to path: {parent_dir}")

try:
    print("Verifying imports...")
    # Mock environment variables if needed
    os.environ["MONGO_URI"] = "mongodb://localhost:27017"
    os.environ["MONGO_DB"] = "test_db"
    
    from app.main import app
    print("OK: app.main imported")
    from routes.ingest import router as ingest_router
    print("OK: routes.ingest imported")
    from services.chunk_builder import build_chunks
    print("OK: services.chunk_builder imported")
    from services.chapter_pipeline import build_chapters
    print("OK: services.chapter_pipeline imported")
    
    print("\n[SUCCESS] All critical modules imported successfully!")
except Exception as e:
    print(f"\n❌ Verification Failed: {e}")
    # Print traceback for details
    import traceback
    traceback.print_exc()
    sys.exit(1)
