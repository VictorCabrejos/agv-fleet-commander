#!/usr/bin/env python3
"""
Script de prueba para verificar navegación entre dashboard y landing page
"""

import requests
import time


def test_navigation():
    """Prueba la navegación entre las páginas"""
    base_url = "http://localhost:5001"

    print("🧪 Probando navegación del sistema AGV Fleet Commander")

    # Test dashboard
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Dashboard accesible en http://localhost:5001/")
        else:
            print(f"❌ Dashboard no disponible: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Servidor no está corriendo en puerto 5001")
        return

    # Test landing page
    try:
        response = requests.get(f"{base_url}/landing")
        if response.status_code == 200:
            print("✅ Landing page accesible en http://localhost:5001/landing")
        else:
            print(f"❌ Landing page no disponible: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ No se puede acceder al landing page")

    # Test API endpoints
    endpoints = ["/api/agvs", "/api/tasks", "/api/metrics", "/api/optimize"]
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}")
            if response.status_code == 200:
                print(f"✅ API {endpoint} funcionando")
            else:
                print(f"⚠️ API {endpoint}: {response.status_code}")
        except:
            print(f"❌ Error en API {endpoint}")


if __name__ == "__main__":
    test_navigation()
