"""
Main API - AGV Fleet Commander
FastAPI application para el sistema de gestión de flota AGV
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import uvicorn

from config import config
from domain.entities import Position, TaskPriority
from domain.services import FleetOrchestrationService, AGVControlService
from adapters.data_adapter import CSVDataAdapter, SimulationDataUpdater
from adapters.openai_adapter import OpenAIRouteOptimizer, OpenAIAnalytics
from adapters.notification_adapter import LoggingNotificationAdapter


# Modelos Pydantic para API
class PositionModel(BaseModel):
    x: float
    y: float


class CreateTaskModel(BaseModel):
    description: str
    origin: PositionModel
    destination: PositionModel
    priority: str = "MEDIUM"
    container_id: Optional[str] = None


class MoveAGVModel(BaseModel):
    agv_id: str
    position: PositionModel


class EmergencyTaskModel(BaseModel):
    description: str
    origin: PositionModel
    destination: PositionModel
    container_id: Optional[str] = None


# Crear aplicación FastAPI
app = FastAPI(
    title="AGV Fleet Commander",
    description="Sistema Inteligente de Gestión de Flota AGV - Puerto de Chancay",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Variables globales para servicios
fleet_service: FleetOrchestrationService = None
agv_control_service: AGVControlService = None
simulation_updater: SimulationDataUpdater = None
simulation_task: asyncio.Task = None


@app.on_event("startup")
async def startup_event():
    """Inicializar servicios al iniciar la aplicación"""
    global fleet_service, agv_control_service, simulation_updater, simulation_task

    print("🚀 Iniciando AGV Fleet Commander...")

    # Verificar configuración
    if not config.openai.api_key:
        print("⚠️ ADVERTENCIA: No se ha configurado OPENAI_API_KEY")
        print("   Algunas funciones de IA no estarán disponibles")

    try:
        # Inicializar adaptadores
        data_adapter = CSVDataAdapter(config.system.data_directory)
        notification_adapter = LoggingNotificationAdapter(config.system.logs_directory)

        # Inicializar servicios de IA solo si hay API key
        if config.openai.api_key:
            route_optimizer = OpenAIRouteOptimizer(config.openai.api_key)
            ai_analytics = OpenAIAnalytics(config.openai.api_key)
        else:
            # Usar adaptadores mock o básicos
            route_optimizer = None
            ai_analytics = None

        # Inicializar servicios de dominio
        fleet_service = FleetOrchestrationService(
            agv_repository=data_adapter,
            task_repository=data_adapter,
            route_optimizer=route_optimizer,
            ai_analytics=ai_analytics,
            notification_service=notification_adapter,
        )

        agv_control_service = AGVControlService(
            agv_repository=data_adapter, notification_service=notification_adapter
        )

        # Inicializar simulación si está habilitada
        if config.system.simulation_enabled:
            simulation_updater = SimulationDataUpdater(data_adapter)
            simulation_task = asyncio.create_task(run_simulation())

        print("✅ AGV Fleet Commander iniciado exitosamente")
        print(f"📊 Dashboard disponible en: http://{config.host}:{config.port}")
        print(f"📖 API Docs en: http://{config.host}:{config.port}/api/docs")

    except Exception as e:
        print(f"❌ Error iniciando la aplicación: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Limpiar recursos al cerrar la aplicación"""
    global simulation_task

    print("🛑 Cerrando AGV Fleet Commander...")

    if simulation_task:
        simulation_task.cancel()
        try:
            await simulation_task
        except asyncio.CancelledError:
            pass

    print("✅ AGV Fleet Commander cerrado exitosamente")


async def run_simulation():
    """Ejecutar simulación en background"""
    while True:
        try:
            if simulation_updater:
                simulation_updater.simulate_agv_movement()
                simulation_updater.simulate_battery_changes()

            # Esperar según velocidad de simulación
            await asyncio.sleep(5.0 / config.system.simulation_speed)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error en simulación: {e}")
            await asyncio.sleep(10)


# Ruta del Landing Page
@app.get("/landing", response_class=HTMLResponse)
async def landing_page():
    """Landing page vendedor del sistema"""
    try:
        with open("templates/landing.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Landing page not found</h1><p>El archivo templates/landing.html no existe.</p>",
            status_code=404,
        )


# Ruta principal - Dashboard
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dashboard principal del sistema"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AGV Fleet Commander</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {
                theme: {
                    extend: {
                        colors: {
                            'chancay': {
                                50: '#f0f9ff',
                                500: '#0ea5e9',
                                600: '#0284c7',
                                700: '#0369a1'
                            }
                        }
                    }
                }
            }
        </script>
    </head>
    <body class="bg-gray-50">
        <div id="app">
            <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
                <!-- Header -->
                <header class="bg-white shadow-lg border-b-4 border-chancay-500">
                    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div class="flex justify-between items-center py-6">
                            <div class="flex items-center space-x-4">
                                <div class="w-12 h-12 bg-chancay-500 rounded-lg flex items-center justify-center">
                                    <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/>
                                    </svg>
                                </div>
                                <div>
                                    <h1 class="text-2xl font-bold text-gray-900">AGV Fleet Commander</h1>
                                    <p class="text-sm text-gray-600">Sistema Inteligente de Gestión de Flota • Puerto de Chancay</p>
                                </div>
                            </div>
                            <div class="flex items-center space-x-4">
                                <a href="/landing" class="text-chancay-600 hover:text-chancay-700 font-medium text-sm transition-colors">
                                    🌟 Landing Page
                                </a>
                                <div class="flex items-center space-x-2">
                                    <div class="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                                    <span class="text-sm font-medium text-gray-700">Sistema Operativo</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </header>

                <!-- Main Content -->
                <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <!-- Status Cards -->
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <div class="bg-white rounded-xl shadow-lg p-6 border-l-4 border-green-500">
                            <div class="flex items-center">
                                <div class="flex-shrink-0">
                                    <div class="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
                                        <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                        </svg>
                                    </div>
                                </div>
                                <div class="ml-4">
                                    <p class="text-sm font-medium text-gray-600">AGVs Activos</p>
                                    <p class="text-2xl font-bold text-gray-900" id="active-agvs">-</p>
                                </div>
                            </div>
                        </div>

                        <div class="bg-white rounded-xl shadow-lg p-6 border-l-4 border-blue-500">
                            <div class="flex items-center">
                                <div class="flex-shrink-0">
                                    <div class="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                                        <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
                                        </svg>
                                    </div>
                                </div>
                                <div class="ml-4">
                                    <p class="text-sm font-medium text-gray-600">Tareas Pendientes</p>
                                    <p class="text-2xl font-bold text-gray-900" id="pending-tasks">-</p>
                                </div>
                            </div>
                        </div>

                        <div class="bg-white rounded-xl shadow-lg p-6 border-l-4 border-yellow-500">
                            <div class="flex items-center">
                                <div class="flex-shrink-0">
                                    <div class="w-8 h-8 bg-yellow-500 rounded-lg flex items-center justify-center">
                                        <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                        </svg>
                                    </div>
                                </div>
                                <div class="ml-4">
                                    <p class="text-sm font-medium text-gray-600">Batería Promedio</p>
                                    <p class="text-2xl font-bold text-gray-900" id="avg-battery">-</p>
                                </div>
                            </div>
                        </div>

                        <div class="bg-white rounded-xl shadow-lg p-6 border-l-4 border-purple-500">
                            <div class="flex items-center">
                                <div class="flex-shrink-0">
                                    <div class="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                                        <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v4"/>
                                        </svg>
                                    </div>
                                </div>
                                <div class="ml-4">
                                    <p class="text-sm font-medium text-gray-600">Eficiencia</p>
                                    <p class="text-2xl font-bold text-gray-900" id="efficiency">-</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                        <button onclick="assignTasks()" class="bg-chancay-500 hover:bg-chancay-600 text-white font-bold py-4 px-6 rounded-xl shadow-lg transition-colors duration-200">
                            🤖 Asignar Tareas con IA
                        </button>
                        <button onclick="optimizeRoutes()" class="bg-green-500 hover:bg-green-600 text-white font-bold py-4 px-6 rounded-xl shadow-lg transition-colors duration-200">
                            🛣️ Optimizar Rutas
                        </button>
                        <button onclick="generateInsights()" class="bg-purple-500 hover:bg-purple-600 text-white font-bold py-4 px-6 rounded-xl shadow-lg transition-colors duration-200">
                            💡 Generar Insights IA
                        </button>
                    </div>

                    <!-- Content Tabs -->
                    <div class="bg-white rounded-xl shadow-lg">
                        <div class="border-b border-gray-200">
                            <nav class="flex space-x-8 px-6">
                                <button onclick="showTab('fleet')" class="tab-button py-4 px-1 border-b-2 border-chancay-500 text-chancay-600 font-medium text-sm">
                                    Estado de Flota
                                </button>
                                <button onclick="showTab('tasks')" class="tab-button py-4 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm">
                                    Tareas
                                </button>
                                <button onclick="showTab('insights')" class="tab-button py-4 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm">
                                    Insights IA
                                </button>
                            </nav>
                        </div>

                        <div class="p-6">
                            <div id="content-area">
                                <div class="text-center py-8">
                                    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-chancay-500 mx-auto mb-4"></div>
                                    <p class="text-gray-600">Cargando datos de la flota...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
        </div>

        <script>
            let currentTab = 'fleet';

            // Cargar datos iniciales
            document.addEventListener('DOMContentLoaded', function() {
                loadFleetOverview();
                setInterval(loadFleetOverview, 10000); // Actualizar cada 10 segundos
            });

            async function loadFleetOverview() {
                try {
                    const response = await fetch('/api/fleet/overview');
                    const data = await response.json();

                    // Actualizar métricas en tarjetas
                    document.getElementById('active-agvs').textContent = data.fleet_metrics.active_agvs;
                    document.getElementById('pending-tasks').textContent = data.fleet_metrics.pending_tasks;
                    document.getElementById('avg-battery').textContent = data.fleet_metrics.average_battery.toFixed(1) + '%';
                    document.getElementById('efficiency').textContent = (data.fleet_metrics.fleet_efficiency * 100).toFixed(1) + '%';

                    // Mostrar contenido según tab activa
                    if (currentTab === 'fleet') {
                        showFleetData(data);
                    }
                } catch (error) {
                    console.error('Error cargando datos:', error);
                }
            }

            function showTab(tab) {
                currentTab = tab;

                // Actualizar tabs visuales
                document.querySelectorAll('.tab-button').forEach(btn => {
                    btn.className = 'tab-button py-4 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm';
                });
                event.target.className = 'tab-button py-4 px-1 border-b-2 border-chancay-500 text-chancay-600 font-medium text-sm';

                // Cargar contenido según tab
                if (tab === 'fleet') {
                    loadFleetOverview();
                } else if (tab === 'tasks') {
                    loadTasks();
                } else if (tab === 'insights') {
                    loadInsights();
                }
            }

            function showFleetData(data) {
                const content = `
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900 mb-4">AGVs en Operación</h3>
                            <div class="space-y-3">
                                ${data.agvs.map(agv => `
                                    <div class="bg-gray-50 rounded-lg p-4 border-l-4 ${getAGVBorderColor(agv.status)}">
                                        <div class="flex justify-between items-start">
                                            <div>
                                                <h4 class="font-medium text-gray-900">${agv.name} (${agv.agv_id})</h4>
                                                <p class="text-sm text-gray-600">Estado: ${getStatusLabel(agv.status)}</p>
                                                <p class="text-sm text-gray-600">Posición: (${agv.position.x.toFixed(1)}, ${agv.position.y.toFixed(1)})</p>
                                            </div>
                                            <div class="text-right">
                                                <div class="text-lg font-bold ${getBatteryColor(agv.battery_level)}">${agv.battery_level.toFixed(1)}%</div>
                                                <div class="text-xs text-gray-500">Batería</div>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>

                        <div>
                            <h3 class="text-lg font-semibold text-gray-900 mb-4">Métricas de Rendimiento</h3>
                            <div class="bg-gray-50 rounded-lg p-4">
                                <div class="grid grid-cols-2 gap-4">
                                    <div class="text-center">
                                        <div class="text-2xl font-bold text-green-600">${data.fleet_metrics.active_agvs}</div>
                                        <div class="text-sm text-gray-600">Activos</div>
                                    </div>
                                    <div class="text-center">
                                        <div class="text-2xl font-bold text-blue-600">${data.fleet_metrics.idle_agvs}</div>
                                        <div class="text-sm text-gray-600">En Espera</div>
                                    </div>
                                    <div class="text-center">
                                        <div class="text-2xl font-bold text-yellow-600">${data.fleet_metrics.charging_agvs}</div>
                                        <div class="text-sm text-gray-600">Cargando</div>
                                    </div>
                                    <div class="text-center">
                                        <div class="text-2xl font-bold text-purple-600">${(data.fleet_metrics.fleet_efficiency * 100).toFixed(1)}%</div>
                                        <div class="text-sm text-gray-600">Eficiencia</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                document.getElementById('content-area').innerHTML = content;
            }

            function getAGVBorderColor(status) {
                const colors = {
                    'IDLE': 'border-gray-400',
                    'MOVING': 'border-blue-500',
                    'TRANSPORTING': 'border-green-500',
                    'CHARGING': 'border-yellow-500',
                    'MAINTENANCE': 'border-red-500'
                };
                return colors[status] || 'border-gray-400';
            }

            function getStatusLabel(status) {
                const labels = {
                    'IDLE': 'En Espera',
                    'MOVING': 'En Movimiento',
                    'TRANSPORTING': 'Transportando',
                    'CHARGING': 'Cargando',
                    'MAINTENANCE': 'Mantenimiento'
                };
                return labels[status] || status;
            }

            function getBatteryColor(level) {
                if (level > 70) return 'text-green-600';
                if (level > 30) return 'text-yellow-600';
                return 'text-red-600';
            }

            async function assignTasks() {
                try {
                    const response = await fetch('/api/fleet/assign-tasks', { method: 'POST' });
                    const result = await response.json();
                    alert(`✅ ${result.message}\\nTareas asignadas: ${result.total_assigned}`);
                    loadFleetOverview();
                } catch (error) {
                    alert('❌ Error asignando tareas: ' + error.message);
                }
            }

            async function optimizeRoutes() {
                try {
                    const response = await fetch('/api/fleet/optimize-routes', { method: 'POST' });
                    const result = await response.json();
                    alert(`✅ ${result.message}\\nRutas optimizadas: ${result.total_routes}`);
                } catch (error) {
                    alert('❌ Error optimizando rutas: ' + error.message);
                }
            }

            async function generateInsights() {
                try {
                    showTab('insights');
                    loadInsights();
                } catch (error) {
                    alert('❌ Error generando insights: ' + error.message);
                }
            }

            async function loadTasks() {
                // Implementar carga de tareas
                document.getElementById('content-area').innerHTML = '<p class="text-center text-gray-600">Funcionalidad de tareas en desarrollo...</p>';
            }

            async function loadInsights() {
                document.getElementById('content-area').innerHTML = '<div class="text-center"><div class="animate-spin rounded-full h-8 w-8 border-b-2 border-chancay-500 mx-auto mb-4"></div><p class="text-gray-600">Generando insights con IA...</p></div>';

                try {
                    const response = await fetch('/api/ai/insights');
                    const insights = await response.json();

                    const content = `
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900 mb-4">🤖 Insights Generados por IA</h3>
                            <div class="space-y-4">
                                ${insights.map(insight => `
                                    <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border-l-4 border-blue-500">
                                        <div class="flex justify-between items-start mb-2">
                                            <h4 class="font-medium text-gray-900">${insight.title}</h4>
                                            <span class="text-xs px-2 py-1 rounded-full ${getImpactColor(insight.impact)} text-white">${insight.impact}</span>
                                        </div>
                                        <p class="text-gray-700 mb-2">${insight.description}</p>
                                        <p class="text-sm text-blue-700 font-medium">💡 ${insight.recommendation}</p>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                    document.getElementById('content-area').innerHTML = content;
                } catch (error) {
                    document.getElementById('content-area').innerHTML = '<p class="text-center text-red-600">❌ Error generando insights: ' + error.message + '</p>';
                }
            }

            function getImpactColor(impact) {
                const colors = {
                    'LOW': 'bg-green-500',
                    'MEDIUM': 'bg-yellow-500',
                    'HIGH': 'bg-orange-500',
                    'CRITICAL': 'bg-red-500'
                };
                return colors[impact] || 'bg-gray-500';
            }
        </script>
    </body>
    </html>
    """


# API Endpoints
@app.get("/api/fleet/overview")
async def get_fleet_overview():
    """Obtener vista general de la flota"""
    try:
        overview = fleet_service.get_fleet_overview()

        # Convertir entidades a diccionarios para JSON
        return {
            "fleet_metrics": {
                "total_agvs": overview["fleet_metrics"].total_agvs,
                "active_agvs": overview["fleet_metrics"].active_agvs,
                "idle_agvs": overview["fleet_metrics"].idle_agvs,
                "charging_agvs": overview["fleet_metrics"].charging_agvs,
                "pending_tasks": overview["fleet_metrics"].pending_tasks,
                "completed_tasks": overview["fleet_metrics"].completed_tasks,
                "average_battery": overview["fleet_metrics"].average_battery,
                "fleet_efficiency": overview["fleet_metrics"].fleet_efficiency,
            },
            "agvs": [
                {
                    "agv_id": agv.agv_id,
                    "name": agv.name,
                    "position": {"x": agv.position.x, "y": agv.position.y},
                    "battery_level": agv.battery_level,
                    "status": agv.status.value,
                    "current_task_id": agv.current_task_id,
                    "last_update": (
                        agv.last_update.isoformat() if agv.last_update else None
                    ),
                }
                for agv in overview["agvs"]
            ],
            "pending_tasks": [
                {
                    "task_id": task.task_id,
                    "description": task.description,
                    "origin": {"x": task.origin.x, "y": task.origin.y},
                    "destination": {"x": task.destination.x, "y": task.destination.y},
                    "priority": task.priority.value,
                    "container_id": task.container_id,
                    "created_at": (
                        task.created_at.isoformat() if task.created_at else None
                    ),
                }
                for task in overview["pending_tasks"]
            ],
            "total_tasks": overview["total_tasks"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo vista de flota: {str(e)}"
        )


@app.post("/api/fleet/assign-tasks")
async def assign_tasks():
    """Asignar tareas de manera óptima"""
    try:
        result = fleet_service.assign_optimal_tasks()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error asignando tareas: {str(e)}")


@app.post("/api/fleet/optimize-routes")
async def optimize_routes():
    """Optimizar rutas de la flota"""
    try:
        result = fleet_service.optimize_fleet_routes()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error optimizando rutas: {str(e)}"
        )


@app.get("/api/ai/insights")
async def get_ai_insights():
    """Obtener insights generados por IA"""
    try:
        insights = fleet_service.generate_ai_insights()
        return insights
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generando insights: {str(e)}"
        )


@app.post("/api/agv/move")
async def move_agv(move_data: MoveAGVModel):
    """Mover AGV a una posición específica"""
    try:
        position = Position(move_data.position.x, move_data.position.y)
        result = agv_control_service.send_agv_to_position(move_data.agv_id, position)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error moviendo AGV: {str(e)}")


@app.post("/api/agv/{agv_id}/emergency-stop")
async def emergency_stop_agv(agv_id: str):
    """Parada de emergencia de AGV"""
    try:
        result = agv_control_service.emergency_stop_agv(agv_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error en parada de emergencia: {str(e)}"
        )


@app.post("/api/tasks/emergency")
async def create_emergency_task(task_data: EmergencyTaskModel):
    """Crear tarea de emergencia"""
    try:
        origin = Position(task_data.origin.x, task_data.origin.y)
        destination = Position(task_data.destination.x, task_data.destination.y)

        result = fleet_service.create_emergency_task(
            description=task_data.description,
            origin=origin,
            destination=destination,
            container_id=task_data.container_id,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creando tarea de emergencia: {str(e)}"
        )


@app.get("/api/system/status")
async def get_system_status():
    """Obtener estado del sistema"""
    return {
        "system": "AGV Fleet Commander",
        "version": "1.0.0",
        "status": "OPERATIONAL",
        "timestamp": datetime.now().isoformat(),
        "config": config.get_summary(),
        "simulation_enabled": config.system.simulation_enabled,
    }


@app.get("/api/system/health")
async def health_check():
    """Health check del sistema"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "fleet_service": "operational" if fleet_service else "unavailable",
            "agv_control": "operational" if agv_control_service else "unavailable",
            "simulation": (
                "running"
                if simulation_task and not simulation_task.done()
                else "stopped"
            ),
        },
    }


# Punto de entrada principal
def main():
    """Función principal para ejecutar la aplicación"""
    print("🤖 AGV Fleet Commander - Sistema Inteligente de Gestión de Flota")
    print("🏗️ Arquitectura Hexagonal + IA para Puerto de Chancay")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
