import os
from datetime import datetime
from dateutil import parser as dateparser
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect

# =============================
# DB URLの構築（必ずPostgreSQLを使う）
# =============================
def _build_db_uri():
    url = os.environ.get('DATABASE_URL')
    if not url:
        return 'sqlite:///reservations.db'  # ローカル開発用
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif url.startswith('postgresql://') and '+psycopg' not in url:
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = _build_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 接続切断対策
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 300  # 5分ごとに再接続
}

db = SQLAlchemy(app)

# =============================
# モデル定義
# =============================
class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    note = db.Column(db.String(200), nullable=True)

    def to_event(self):
        return {
            "id": self.id,
            "title": f"{self.user}" + (f" — {self.note}" if self.note else ""),
            "start": self.start_time.isoformat(),
            "end": self.end_time.isoformat(),
        }

# =============================
# 起動時に必ずテーブル作成
# =============================
with app.app_context():
    db.create_all()
    print("[INIT] Tables:", inspect(db.engine).get_table_names())

@app.route("/initdb")
def init_db():
    with app.app_context():
        db.create_all()
        tables = inspect(db.engine).get_table_names()
        return jsonify({"status": "ok", "tables": tables})

# =============================
# ユーティリティ関数
# =============================
def overlaps(start, end, exclude_id=None):
    """Return True if [start, end) overlaps an existing reservation"""
    q = Reservation.query.filter(
        Reservation.start_time < end,
        Reservation.end_time > start
    )
    if exclude_id is not None:
        q = q.filter(Reservation.id != exclude_id)
    return db.session.query(q.exists()).scalar()

# =============================
# ルート定義
# =============================
@app.route('/healthz')
def healthz():
    return 'ok', 200

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events')
def events():
    res = Reservation.query.order_by(Reservation.start_time.asc()).all()
    return jsonify([r.to_event() for r in res])

@app.route('/reserve', methods=['POST'])
def reserve():
    try:
        user = request.form['user'].strip()
        start_raw = request.form['start']
        end_raw = request.form['end']
        note = request.form.get('note', '').strip() or None

        start = dateparser.parse(start_raw)
        end = dateparser.parse(end_raw)

        if end <= start:
            flash('終了時刻は開始時刻より後である必要があります。', 'error')
            return redirect(url_for('index'))

        if overlaps(start, end):
            flash('その時間帯はすでに予約があります。別の時間を選んでください。', 'error')
            return redirect(url_for('index'))

        r = Reservation(user=user, start_time=start, end_time=end, note=note)
        db.session.add(r)
        db.session.commit()
        flash('予約を作成しました。', 'success')
    except Exception as e:
        print('reserve error:', e)
        flash('予約の作成に失敗しました。入力内容を確認してください。', 'error')
    return redirect(url_for('index'))

@app.route('/delete/<int:rid>', methods=['POST'])
def delete(rid):
    r = Reservation.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    flash('予約を削除しました。', 'success')
    return redirect(url_for('index'))

@app.route('/reservations')
def list_reservations():
    res = Reservation.query.order_by(Reservation.start_time.asc()).all()
    return render_template('list.html', reservations=res)

@app.cli.command('init-db')
def init_db_cmd():
    """Initialize the database: flask init-db"""
    db.create_all()
    print('Initialized the database.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
