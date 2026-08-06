import datetime
from sqlalchemy.orm import Session
from app.database import engine, Base, SessionLocal
from app.models import Branch, User, Book, BookCopy, Transaction, Notification
from app.controllers.auth_controller import get_password_hash
from app.services.qr_service import generate_qr_token

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(Branch).count() > 0:
            print("[SEED] Database already populated with seed data.")
            return

        print("[SEED] Starting database initialization for Effutu Municipal Library Network...")

        # 1. Seed 19 Target Branches (4 active initially)
        branches_data = [
            {"code": "BR-EFF-01", "name": "Effutu Central Library (HQ)", "location": "Winneba Town Center", "status": "active", "is_hq": True},
            {"code": "BR-EFF-02", "name": "Winneba Community Library", "location": "Commercial Street, Winneba", "status": "active", "is_hq": False},
            {"code": "BR-EFF-03", "name": "South Campus Academic Library", "location": "UEW South Campus", "status": "active", "is_hq": False},
            {"code": "BR-EFF-04", "name": "North Campus Digital & Reference Library", "location": "UEW North Campus", "status": "active", "is_hq": False},
        ]
        
        # Add 15 Target expansion branches to complete the 19 target branches requirement
        target_locations = [
            "Atekyedo Community", "Kwali Krew", "Gyahadze Branch", "Akosua Village Library",
            "Nsimbo Library", "Abasraba Center", "Eyipey Community", "Sankor Sub-Library",
            "Ghartey Hall Branch", "Osubonpanyin", "Pomadze Hub", "Winneba Junction Branch",
            "Essuekyir Library", "Woarababa Post", "Zongo Ward Library"
        ]

        for i, loc in enumerate(target_locations, start=5):
            branches_data.append({
                "code": f"BR-EFF-{i:02d}",
                "name": f"{loc} Branch Library",
                "location": f"{loc}, Effutu",
                "status": "target",
                "is_hq": False
            })

        db_branches = []
        for b in branches_data:
            br = Branch(**b)
            db.add(br)
            db_branches.append(br)
        db.commit()
        print(f"[SEED] Created {len(db_branches)} branches (4 active, 15 target).")

        # 2. Seed Default Users for Each Role
        hashed_pw = get_password_hash("admin123")

        # System Admin
        sys_admin = User(
            member_id="EFF-SYS-0001",
            full_name="Dr. Kwame Essel (System Admin)",
            email="sysadmin@effutulibrary.gov.gh",
            hashed_password=hashed_pw,
            role="sys_admin",
            branch_id=db_branches[0].id,
            ghana_card_number="GHA-000000001-1",
            is_approved=True,
            is_active=True,
            must_change_password=False,
            is_physically_verified=True
        )

        # HQ Admin
        hq_admin = User(
            member_id="EFF-HQ-0002",
            full_name="Abena Ghartey (HQ Admin)",
            email="hqadmin@effutulibrary.gov.gh",
            hashed_password=hashed_pw,
            role="hq_admin",
            branch_id=db_branches[0].id,
            ghana_card_number="GHA-000000002-2",
            is_approved=True,
            is_active=True,
            must_change_password=False,
            is_physically_verified=True
        )

        # Librarian (Winneba Community Library)
        librarian = User(
            member_id="EFF-LIB-0003",
            full_name="Kofi Ofori (Branch Librarian)",
            email="librarian@effutulibrary.gov.gh",
            hashed_password=hashed_pw,
            role="librarian",
            branch_id=db_branches[1].id,
            ghana_card_number="GHA-000000003-3",
            is_approved=True,
            is_active=True,
            must_change_password=False,
            is_physically_verified=True
        )

        # Approved Patron
        patron = User(
            member_id="EFF-MBR-1001",
            full_name="Kojo Mensah (Student)",
            email="patron@effutulibrary.gov.gh",
            hashed_password=hashed_pw,
            role="patron",
            branch_id=db_branches[0].id,
            ghana_card_number="GHA-123456789-1",
            is_approved=True,
            is_active=True,
            must_change_password=False,
            is_physically_verified=True
        )

        # Pending Patron (Awaiting Physical Ghana Card Verification)
        pending_patron = User(
            member_id="EFF-MBR-1002",
            full_name="Ama Serwaa",
            email="pending_patron@gmail.com",
            hashed_password=hashed_pw,
            role="patron",
            branch_id=db_branches[1].id,
            ghana_card_number="GHA-987654321-9",
            is_approved=True,
            is_active=True,
            must_change_password=True,
            is_physically_verified=False
        )

        db.add_all([sys_admin, hq_admin, librarian, patron, pending_patron])

        db.commit()
        print("[SEED] Created role users: System Admin, HQ Admin, Librarian, Patron, Pending Patron.")

        # 3. Seed WASSCE & Master Book Catalog
        books_data = [
            {
                "title": "WASSCE Integrated Science Core",
                "author": "Dr. E. K. Baidoo",
                "isbn": "9789988123011",
                "publisher": "Asempa Publishers Ghana",
                "pub_year": 2022,
                "category": "WASSCE",
                "cover_url": "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=300",
                "description": "Comprehensive Core Science syllabus preparation for West African Senior School Certificate Examination (WASSCE)."
            },
            {
                "title": "WASSCE Core Mathematics for Senior High Schools",
                "author": "Prof. J. A. Aryeetey",
                "isbn": "9789988123028",
                "publisher": "Ghana Universities Press",
                "pub_year": 2023,
                "category": "Mathematics",
                "cover_url": "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=300",
                "description": "Full algebra, trigonometry, geometry and statistics textbook for WASSCE candidates in Ghana."
            },
            {
                "title": "History of Winneba & Effutu State",
                "author": "Nana Ghartey VII",
                "isbn": "9789988123035",
                "publisher": "Winneba Heritage Trust",
                "pub_year": 2019,
                "category": "General Literature",
                "cover_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=300",
                "description": "Historical documentation of Aboakyer festival, Effutu traditions, and Central Region heritage."
            },
            {
                "title": "Clean Code: Refactoring & Architecture",
                "author": "Robert C. Martin",
                "isbn": "9780132350884",
                "publisher": "Prentice Hall",
                "pub_year": 2008,
                "category": "Science",
                "cover_url": "https://images.unsplash.com/photo-1516979187457-637abb4f9353?w=300",
                "description": "Agile software craftsmanship handbook."
            }
        ]

        for b_dict in books_data:
            book = Book(**b_dict)
            db.add(book)
            db.commit()
            db.refresh(book)

            # Create Book Copies across active branches
            for br in db_branches[:2]:
                qr_tok = generate_qr_token(book.id, br.id)
                copy = BookCopy(
                    book_id=book.id,
                    branch_id=br.id,
                    copy_code=f"B{book.id}-BR{br.id}-01",
                    qr_token=qr_tok,
                    status="available"
                )
                db.add(copy)
        
        db.commit()
        print("[SEED] Master book catalog and inventory copies initialized successfully.")

    except Exception as e:
        db.rollback()
        print(f"[SEED ERROR] {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
