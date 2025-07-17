"""
Data Adapter - AGV Fleet Commander
Adaptador para manejo de datos (simula base de datos en memoria)
"""

import json
import csv
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import random
from pathlib import Path

from domain.entities import AGV, Task, Route, Position, AGVStatus, TaskPriority
from domain.ports import AGVRepositoryPort, TaskRepositoryPort


class CSVDataAdapter(AGVRepositoryPort, TaskRepositoryPort):
    """
    Adaptador que simula una base de datos usando CSV y memoria
    Implementa tanto AGVRepositoryPort como TaskRepositoryPort
    """

    def __init__(self, data_directory: str = "data"):
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(exist_ok=True)

        # Almacenamiento en memoria para simulación
        self._agvs: Dict[str, AGV] = {}
        self._tasks: Dict[str, Task] = {}

        # Archivos CSV
        self.agvs_file = self.data_directory / "agvs.csv"
        self.tasks_file = self.data_directory / "tasks.csv"

        # Inicializar datos si no existen
        self._initialize_sample_data()
        self._load_data()

    def _initialize_sample_data(self):
        """Inicializar datos de muestra si no existen archivos"""
        if not self.agvs_file.exists():
            self._create_sample_agvs()
        if not self.tasks_file.exists():
            self._create_sample_tasks()

    def _create_sample_agvs(self):
        """Crear AGVs de muestra realistas para Puerto de Chancay"""
        sample_agvs = [
            {
                "agv_id": "AGV-001",
                "name": "Alfa Prime",
                "position_x": 100.0,
                "position_y": 50.0,
                "battery_level": 85.5,
                "status": "IDLE",
                "current_task_id": "",
                "last_update": datetime.now().isoformat(),
            },
            {
                "agv_id": "AGV-002",
                "name": "Beta Runner",
                "position_x": 250.0,
                "position_y": 120.0,
                "battery_level": 92.0,
                "status": "MOVING",
                "current_task_id": "TSK-001",
                "last_update": datetime.now().isoformat(),
            },
            {
                "agv_id": "AGV-003",
                "name": "Gamma Loader",
                "position_x": 180.0,
                "position_y": 200.0,
                "battery_level": 67.3,
                "status": "TRANSPORTING",
                "current_task_id": "TSK-002",
                "last_update": datetime.now().isoformat(),
            },
            {
                "agv_id": "AGV-004",
                "name": "Delta Force",
                "position_x": 320.0,
                "position_y": 80.0,
                "battery_level": 15.8,
                "status": "CHARGING",
                "current_task_id": "",
                "last_update": datetime.now().isoformat(),
            },
            {
                "agv_id": "AGV-005",
                "name": "Echo Navigator",
                "position_x": 75.0,
                "position_y": 300.0,
                "battery_level": 88.2,
                "status": "IDLE",
                "current_task_id": "",
                "last_update": datetime.now().isoformat(),
            },
            {
                "agv_id": "AGV-006",
                "name": "Foxtrot Express",
                "position_x": 400.0,
                "position_y": 150.0,
                "battery_level": 73.9,
                "status": "MOVING",
                "current_task_id": "TSK-003",
                "last_update": datetime.now().isoformat(),
            },
        ]

        # Escribir CSV
        with open(self.agvs_file, "w", newline="", encoding="utf-8") as f:
            if sample_agvs:
                writer = csv.DictWriter(f, fieldnames=sample_agvs[0].keys())
                writer.writeheader()
                writer.writerows(sample_agvs)

    def _create_sample_tasks(self):
        """Crear tareas de muestra realistas"""
        base_time = datetime.now()
        sample_tasks = [
            {
                "task_id": "TSK-001",
                "description": "Transportar contenedor MSKU-2345678 a zona de almacenamiento A-12",
                "origin_x": 250.0,
                "origin_y": 120.0,
                "destination_x": 180.0,
                "destination_y": 200.0,
                "priority": "HIGH",
                "container_id": "MSKU-2345678",
                "assigned_agv_id": "AGV-002",
                "created_at": base_time.isoformat(),
                "started_at": (base_time + timedelta(minutes=5)).isoformat(),
                "completed_at": "",
            },
            {
                "task_id": "TSK-002",
                "description": "Mover contenedor COSCO-9876543 desde nave a terminal",
                "origin_x": 180.0,
                "origin_y": 200.0,
                "destination_x": 350.0,
                "destination_y": 280.0,
                "priority": "HIGH",
                "container_id": "COSCO-9876543",
                "assigned_agv_id": "AGV-003",
                "created_at": (base_time - timedelta(minutes=10)).isoformat(),
                "started_at": (base_time - timedelta(minutes=5)).isoformat(),
                "completed_at": "",
            },
            {
                "task_id": "TSK-003",
                "description": "Recoger contenedor EVERGREEN-1122334 en zona C-08",
                "origin_x": 400.0,
                "origin_y": 150.0,
                "destination_x": 120.0,
                "destination_y": 350.0,
                "priority": "MEDIUM",
                "container_id": "EVERGREEN-1122334",
                "assigned_agv_id": "AGV-006",
                "created_at": (base_time + timedelta(minutes=2)).isoformat(),
                "started_at": (base_time + timedelta(minutes=8)).isoformat(),
                "completed_at": "",
            },
            {
                "task_id": "TSK-004",
                "description": "Transportar contenedor vacío a zona de lavado",
                "origin_x": 75.0,
                "origin_y": 300.0,
                "destination_x": 450.0,
                "destination_y": 100.0,
                "priority": "LOW",
                "container_id": "EMPTY-001",
                "assigned_agv_id": "",
                "created_at": (base_time + timedelta(minutes=15)).isoformat(),
                "started_at": "",
                "completed_at": "",
            },
            {
                "task_id": "TSK-005",
                "description": "🚨 URGENTE: Retirar contenedor peligroso HAZMAT-5555",
                "origin_x": 200.0,
                "origin_y": 250.0,
                "destination_x": 500.0,
                "destination_y": 50.0,
                "priority": "URGENT",
                "container_id": "HAZMAT-5555",
                "assigned_agv_id": "",
                "created_at": (base_time + timedelta(minutes=20)).isoformat(),
                "started_at": "",
                "completed_at": "",
            },
        ]

        # Escribir CSV
        with open(self.tasks_file, "w", newline="", encoding="utf-8") as f:
            if sample_tasks:
                writer = csv.DictWriter(f, fieldnames=sample_tasks[0].keys())
                writer.writeheader()
                writer.writerows(sample_tasks)

    def _load_data(self):
        """Cargar datos desde CSV a memoria"""
        # Cargar AGVs
        if self.agvs_file.exists():
            with open(self.agvs_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    agv = AGV(
                        agv_id=row["agv_id"],
                        name=row["name"],
                        position=Position(
                            float(row["position_x"]), float(row["position_y"])
                        ),
                        battery_level=float(row["battery_level"]),
                        status=AGVStatus(row["status"]),
                        current_task_id=(
                            row["current_task_id"] if row["current_task_id"] else None
                        ),
                        last_update=(
                            datetime.fromisoformat(row["last_update"])
                            if row["last_update"]
                            else None
                        ),
                    )
                    self._agvs[agv.agv_id] = agv

        # Cargar Tasks
        if self.tasks_file.exists():
            with open(self.tasks_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    task = Task(
                        task_id=row["task_id"],
                        description=row["description"],
                        origin=Position(float(row["origin_x"]), float(row["origin_y"])),
                        destination=Position(
                            float(row["destination_x"]), float(row["destination_y"])
                        ),
                        priority=TaskPriority(row["priority"]),
                        container_id=(
                            row["container_id"] if row["container_id"] else None
                        ),
                        assigned_agv_id=(
                            row["assigned_agv_id"] if row["assigned_agv_id"] else None
                        ),
                        created_at=(
                            datetime.fromisoformat(row["created_at"])
                            if row["created_at"]
                            else datetime.now()
                        ),
                        started_at=(
                            datetime.fromisoformat(row["started_at"])
                            if row["started_at"]
                            else None
                        ),
                        completed_at=(
                            datetime.fromisoformat(row["completed_at"])
                            if row["completed_at"]
                            else None
                        ),
                    )
                    self._tasks[task.task_id] = task

    def _save_agvs(self):
        """Guardar AGVs a CSV"""
        agvs_data = []
        for agv in self._agvs.values():
            agvs_data.append(
                {
                    "agv_id": agv.agv_id,
                    "name": agv.name,
                    "position_x": agv.position.x,
                    "position_y": agv.position.y,
                    "battery_level": agv.battery_level,
                    "status": agv.status.value,
                    "current_task_id": agv.current_task_id or "",
                    "last_update": (
                        agv.last_update.isoformat() if agv.last_update else ""
                    ),
                }
            )

        with open(self.agvs_file, "w", newline="", encoding="utf-8") as f:
            if agvs_data:
                writer = csv.DictWriter(f, fieldnames=agvs_data[0].keys())
                writer.writeheader()
                writer.writerows(agvs_data)

    def _save_tasks(self):
        """Guardar tasks a CSV"""
        tasks_data = []
        for task in self._tasks.values():
            tasks_data.append(
                {
                    "task_id": task.task_id,
                    "description": task.description,
                    "origin_x": task.origin.x,
                    "origin_y": task.origin.y,
                    "destination_x": task.destination.x,
                    "destination_y": task.destination.y,
                    "priority": task.priority.value,
                    "container_id": task.container_id or "",
                    "assigned_agv_id": task.assigned_agv_id or "",
                    "created_at": (
                        task.created_at.isoformat() if task.created_at else ""
                    ),
                    "started_at": (
                        task.started_at.isoformat() if task.started_at else ""
                    ),
                    "completed_at": (
                        task.completed_at.isoformat() if task.completed_at else ""
                    ),
                }
            )

        with open(self.tasks_file, "w", newline="", encoding="utf-8") as f:
            if tasks_data:
                writer = csv.DictWriter(f, fieldnames=tasks_data[0].keys())
                writer.writeheader()
                writer.writerows(tasks_data)

    # Implementación de AGVRepositoryPort
    def get_all_agvs(self) -> List[AGV]:
        """Obtener todos los AGVs"""
        return list(self._agvs.values())

    def get_agv_by_id(self, agv_id: str) -> Optional[AGV]:
        """Obtener AGV por ID"""
        return self._agvs.get(agv_id)

    def get_available_agvs(self) -> List[AGV]:
        """Obtener AGVs disponibles"""
        return [agv for agv in self._agvs.values() if agv.is_available()]

    def update_agv(self, agv: AGV) -> bool:
        """Actualizar AGV"""
        try:
            agv.last_update = datetime.now()
            self._agvs[agv.agv_id] = agv
            self._save_agvs()
            return True
        except Exception:
            return False

    def create_agv(self, agv: AGV) -> bool:
        """Crear nuevo AGV"""
        try:
            if agv.agv_id not in self._agvs:
                self._agvs[agv.agv_id] = agv
                self._save_agvs()
                return True
            return False
        except Exception:
            return False

    # Implementación de TaskRepositoryPort
    def get_all_tasks(self) -> List[Task]:
        """Obtener todas las tareas"""
        return list(self._tasks.values())

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Obtener tarea por ID"""
        return self._tasks.get(task_id)

    def get_pending_tasks(self) -> List[Task]:
        """Obtener tareas pendientes"""
        return [
            task
            for task in self._tasks.values()
            if not task.is_completed() and not task.assigned_agv_id
        ]

    def get_tasks_by_agv(self, agv_id: str) -> List[Task]:
        """Obtener tareas asignadas a un AGV"""
        return [task for task in self._tasks.values() if task.assigned_agv_id == agv_id]

    def create_task(self, task: Task) -> bool:
        """Crear nueva tarea"""
        try:
            if task.task_id not in self._tasks:
                self._tasks[task.task_id] = task
                self._save_tasks()
                return True
            return False
        except Exception:
            return False

    def update_task(self, task: Task) -> bool:
        """Actualizar tarea"""
        try:
            self._tasks[task.task_id] = task
            self._save_tasks()
            return True
        except Exception:
            return False

    def delete_task(self, task_id: str) -> bool:
        """Eliminar tarea"""
        try:
            if task_id in self._tasks:
                del self._tasks[task_id]
                self._save_tasks()
                return True
            return False
        except Exception:
            return False


class SimulationDataUpdater:
    """
    Clase para actualizar datos de simulación en tiempo real
    """

    def __init__(self, data_adapter: CSVDataAdapter):
        self.data_adapter = data_adapter

    def simulate_agv_movement(self):
        """Simular movimiento de AGVs"""
        for agv in self.data_adapter.get_all_agvs():
            if agv.status in [AGVStatus.MOVING, AGVStatus.TRANSPORTING]:
                # Mover AGV hacia su destino (simulación simple)
                if agv.current_task_id:
                    task = self.data_adapter.get_task_by_id(agv.current_task_id)
                    if task:
                        # Mover hacia el destino
                        dx = task.destination.x - agv.position.x
                        dy = task.destination.y - agv.position.y
                        distance = (dx**2 + dy**2) ** 0.5

                        if distance > 5:  # Si no está cerca del destino
                            # Mover un poco hacia el destino
                            move_distance = min(10, distance)
                            factor = move_distance / distance
                            agv.position.x += dx * factor
                            agv.position.y += dy * factor

                            # Consumir batería
                            agv.battery_level = max(
                                0, agv.battery_level - random.uniform(0.1, 0.3)
                            )
                        else:
                            # Llegó al destino
                            agv.position = Position(
                                task.destination.x, task.destination.y
                            )
                            agv.status = AGVStatus.IDLE
                            agv.current_task_id = None
                            task.completed_at = datetime.now()
                            self.data_adapter.update_task(task)

                self.data_adapter.update_agv(agv)

    def simulate_battery_changes(self):
        """Simular cambios de batería"""
        for agv in self.data_adapter.get_all_agvs():
            if agv.status == AGVStatus.CHARGING:
                # Cargar batería
                agv.battery_level = min(100, agv.battery_level + random.uniform(2, 5))
                if agv.battery_level >= 90:
                    agv.status = AGVStatus.IDLE
                self.data_adapter.update_agv(agv)
            elif agv.status == AGVStatus.IDLE:
                # Consumo mínimo en idle
                agv.battery_level = max(
                    0, agv.battery_level - random.uniform(0.01, 0.05)
                )
                if agv.battery_level < 20 and random.random() < 0.3:
                    agv.status = AGVStatus.CHARGING
                self.data_adapter.update_agv(agv)
