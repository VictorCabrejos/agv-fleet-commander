from domain.entities import AGV, AGVStatus, Position


def test_agv_availability_requires_charge_and_idle_state():
    agv = AGV("A-1", "Test", Position(0, 0), 50, AGVStatus.IDLE)
    assert agv.is_available()

    agv.battery_level = 20
    assert not agv.is_available()


def test_position_distance_is_euclidean():
    assert Position(0, 0).distance_to(Position(3, 4)) == 5
