-- Effutu Municipal Library Management System Schema (PostgreSQL)

DROP TABLE IF EXISTS ai_logs CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS book_copies CASCADE;
DROP TABLE IF EXISTS books CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS branches CASCADE;

-- 1. Branches Table (19 target branches, 4 active initially)
CREATE TABLE branches (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    location VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'target', 'inactive')),
    is_hq BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users Table (System Admin, HQ Admin, Librarian, Patron)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    member_id VARCHAR(50) UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL CHECK (role IN ('sys_admin', 'hq_admin', 'librarian', 'patron')),
    branch_id INT REFERENCES branches(id) ON DELETE SET NULL,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Books Table (Master Catalog)
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    isbn VARCHAR(30) UNIQUE,
    publisher VARCHAR(150),
    pub_year INT,
    pages INT,
    category VARCHAR(100) DEFAULT 'General',
    cover_url TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Book Copies Table (Branch inventory & QR tokens)
CREATE TABLE book_copies (
    id SERIAL PRIMARY KEY,
    book_id INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    branch_id INT NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    copy_code VARCHAR(50) UNIQUE NOT NULL,
    qr_token VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(30) DEFAULT 'available' CHECK (status IN ('available', 'issued', 'maintenance', 'reserved')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Transactions Table (Issue & Return, 14 days auto due, GHS 0.50 fine)
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    book_copy_id INT NOT NULL REFERENCES book_copies(id) ON DELETE CASCADE,
    patron_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    issued_by_id INT REFERENCES users(id) ON DELETE SET NULL,
    issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date TIMESTAMP NOT NULL,
    return_date TIMESTAMP,
    fine_amount NUMERIC(10,2) DEFAULT 0.00,
    status VARCHAR(30) DEFAULT 'active' CHECK (status IN ('active', 'returned', 'overdue'))
);

-- 6. Notifications Table (Approval alerts, Overdue reminders via Brevo)
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. AI Query Logs Table
CREATE TABLE ai_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    query TEXT NOT NULL,
    intent VARCHAR(50),
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexing for high-speed lookup & NLP full text search
CREATE INDEX idx_books_isbn ON books(isbn);
CREATE INDEX idx_books_title_author ON books(title, author);
CREATE INDEX idx_book_copies_qr ON book_copies(qr_token);
CREATE INDEX idx_transactions_patron ON transactions(patron_id);
CREATE INDEX idx_transactions_status ON transactions(status);
