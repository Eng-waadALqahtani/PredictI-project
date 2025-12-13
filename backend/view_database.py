"""
Script to view PredictAI database contents.
Run: python backend/view_database.py
"""

import os
import sys
import json
from datetime import datetime

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from db import get_db_session, FingerprintDB, init_db
from sqlalchemy import func

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_section(text):
    print(f"\n{'─'*70}")
    print(f"  {text}")
    print(f"{'─'*70}")

def format_datetime(dt):
    """Format datetime object to readable string"""
    if dt:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return "N/A"

def view_all_fingerprints():
    """View all fingerprints in the database"""
    print_header("🔍 عرض جميع البصمات في قاعدة البيانات")
    
    session = get_db_session()
    try:
        fingerprints = session.query(FingerprintDB).order_by(
            FingerprintDB.created_at.desc()
        ).all()
        
        if not fingerprints:
            print("⚠️  لا توجد بصمات في قاعدة البيانات")
            return
        
        print(f"📊 إجمالي البصمات: {len(fingerprints)}\n")
        
        for idx, fp in enumerate(fingerprints, 1):
            print_section(f"البصمة #{idx}")
            
            print(f"🆔 معرف البصمة:    {fp.fingerprint_id}")
            print(f"👤 معرف المستخدم:  {fp.user_id}")
            print(f"📱 معرف الجهاز:    {fp.device_id or 'N/A'}")
            print(f"🌐 عنوان IP:       {fp.ip_address or 'N/A'}")
            print(f"🖥️  User Agent:     {fp.user_agent[:60] + '...' if fp.user_agent and len(fp.user_agent) > 60 else (fp.user_agent or 'N/A')}")
            print(f"⚠️  درجة الخطر:     {fp.risk_score}/100")
            print(f"📊 الحالة:          {fp.status}")
            print(f"📅 تاريخ الإنشاء:   {format_datetime(fp.created_at)}")
            print(f"🔄 آخر تحديث:       {format_datetime(fp.updated_at)}")
            
            # Behavioral Features
            if fp.behavioral_features_json:
                try:
                    features = json.loads(fp.behavioral_features_json)
                    print(f"\n📈 الخصائص السلوكية:")
                    for key, value in features.items():
                        if key not in ['ip_address', 'user_agent', 'platform']:  # Skip redundant fields
                            print(f"   • {key}: {value}")
                except json.JSONDecodeError:
                    print("   ⚠️  خطأ في قراءة الخصائص السلوكية")
            
            # Related Fingerprints
            if fp.related_fingerprints_json:
                try:
                    related = json.loads(fp.related_fingerprints_json)
                    print(f"\n🔗 البصمات المشابهة ({len(related)}):")
                    for rel in related[:3]:  # Show first 3
                        print(f"   • {rel.get('fingerprint_id', 'N/A')}: similarity={rel.get('similarity', 0):.2%}, status={rel.get('status', 'N/A')}")
                except json.JSONDecodeError:
                    print("   ⚠️  خطأ في قراءة البصمات المشابهة")
            
    finally:
        session.close()

def view_statistics():
    """View database statistics"""
    print_header("📊 إحصائيات قاعدة البيانات")
    
    session = get_db_session()
    try:
        total = session.query(FingerprintDB).count()
        active = session.query(FingerprintDB).filter(FingerprintDB.status == "ACTIVE").count()
        blocked = session.query(FingerprintDB).filter(FingerprintDB.status == "BLOCKED").count()
        cleared = session.query(FingerprintDB).filter(FingerprintDB.status == "CLEARED").count()
        
        high_risk = session.query(FingerprintDB).filter(FingerprintDB.risk_score >= 85).count()
        medium_risk = session.query(FingerprintDB).filter(
            FingerprintDB.risk_score >= 50, 
            FingerprintDB.risk_score < 80
        ).count()
        low_risk = session.query(FingerprintDB).filter(FingerprintDB.risk_score < 50).count()
        
        print(f"📦 إجمالي البصمات:      {total}")
        print(f"\n📊 حسب الحالة:")
        print(f"   ✅ نشطة (ACTIVE):     {active}")
        print(f"   🚫 محظورة (BLOCKED):  {blocked}")
        print(f"   ✓ مُزال المنع (CLEARED): {cleared}")
        
        print(f"\n⚠️  حسب درجة الخطر:")
        print(f"   🔴 عالية (≥80):       {high_risk}")
        print(f"   🟡 متوسطة (50-79):    {medium_risk}")
        print(f"   🟢 منخفضة (<50):      {low_risk}")
        
        # Average risk score
        if total > 0:
            avg_risk = session.query(func.avg(FingerprintDB.risk_score)).scalar()
            print(f"\n📈 متوسط درجة الخطر: {avg_risk:.2f}/100")
        
    finally:
        session.close()

def view_by_user(user_id):
    """View fingerprints for a specific user"""
    print_header(f"👤 عرض بصمات المستخدم: {user_id}")
    
    session = get_db_session()
    try:
        fingerprints = session.query(FingerprintDB).filter(
            FingerprintDB.user_id == user_id
        ).order_by(FingerprintDB.created_at.desc()).all()
        
        if not fingerprints:
            print(f"⚠️  لا توجد بصمات للمستخدم: {user_id}")
            return
        
        print(f"📊 عدد البصمات: {len(fingerprints)}\n")
        
        for idx, fp in enumerate(fingerprints, 1):
            print(f"{idx}. {fp.fingerprint_id} | Risk: {fp.risk_score} | Status: {fp.status} | Created: {format_datetime(fp.created_at)}")
            
    finally:
        session.close()

def export_to_json(output_file="fingerprints_export.json"):
    """Export all fingerprints to JSON file"""
    print_header(f"💾 تصدير البيانات إلى JSON: {output_file}")
    
    session = get_db_session()
    try:
        fingerprints = session.query(FingerprintDB).all()
        
        export_data = []
        for fp in fingerprints:
            export_data.append(fp.to_dict())
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ تم التصدير بنجاح!")
        print(f"📁 الملف: {os.path.abspath(output_file)}")
        print(f"📊 عدد البصمات المُصدّرة: {len(export_data)}")
        
    finally:
        session.close()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='عرض قاعدة بيانات PredictAI')
    parser.add_argument('--user', type=str, help='عرض بصمات مستخدم معين')
    parser.add_argument('--stats', action='store_true', help='عرض الإحصائيات فقط')
    parser.add_argument('--export', type=str, metavar='FILE', help='تصدير البيانات إلى ملف JSON')
    
    args = parser.parse_args()
    
    # Initialize database
    init_db()
    
    if args.export:
        export_to_json(args.export)
    elif args.user:
        view_by_user(args.user)
    elif args.stats:
        view_statistics()
    else:
        # Default: show statistics and all fingerprints
        view_statistics()
        view_all_fingerprints()

if __name__ == "__main__":
    main()

