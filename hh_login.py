#!/usr/bin/env python3
"""Запустите один раз для авторизации в hh.ru."""
from hh_auth import authorize_interactive, get_my_resumes

if __name__ == "__main__":
    token = authorize_interactive()
    resumes = get_my_resumes(token)
    print(f"\nВаши резюме на hh.ru ({len(resumes)}):")
    for r in resumes:
        print(f"  [{r['id']}] {r.get('title', '—')} — {r.get('status', {}).get('name', '')}")
    print("\nГотово! Теперь запускайте: python3 main.py")
