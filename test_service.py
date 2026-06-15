import pytest
import pandas as pd
from service import CardService

@pytest.fixture
def service():
    return CardService()

def test_calculate_mana_value(service):
    assert service.calculate_mana_value("{2}{W}") == 3
    assert service.calculate_mana_value("{5}{R}{R}") == 7
    assert service.calculate_mana_value(None) == 0
    assert service.calculate_mana_value("") == 0

def test_parse_stat(service):
    assert service.parse_stat("4") == 4
    assert service.parse_stat("2.5") == 2
    assert service.parse_stat("invalid") == 0

def test_extraer_colores(service):
    assert service.extraer_colores("['W', 'U']") == {'W', 'U'}
    assert service.extraer_colores("W, U") == {'W', 'U'}
    assert service.extraer_colores(None) == set()
    assert service.extraer_colores([]) == set()

def test_filter_cards(service):
    df = pd.DataFrame([
        {'name': 'Sol Ring', 'type_line': 'Artifact', 'rarity': 'uncommon', 'set_name': 'LEA'},
        {'name': 'Black Lotus', 'type_line': 'Artifact', 'rarity': 'rare', 'set_name': 'LEA'}
    ])
    filtered = service.filter_cards(df, name="Sol")
    assert len(filtered) == 1
    assert filtered.iloc[0]['name'] == 'Sol Ring'

def test_is_legal_in_commander(service):
    cmd_colors = {'W', 'U'}
    row_legal = {'color_identity': "['W']", 'oracle_text': 'Add {W}', 'mana_cost': '{W}'}
    row_illegal = {'color_identity': "['R']", 'oracle_text': 'Add {R}', 'mana_cost': '{R}'}
    
    assert service.is_legal_in_commander(row_legal, cmd_colors) is True
    assert service.is_legal_in_commander(row_illegal, cmd_colors) is False