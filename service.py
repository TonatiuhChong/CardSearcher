import pandas as pd
import re
import ast

class CardService:
    @staticmethod
    def calculate_mana_value(mana_cost):
        if not mana_cost or pd.isna(mana_cost): return 0
        front_cost = str(mana_cost).split(' // ')[0]
        generic = re.findall(r'(\d+)', front_cost)
        generic_sum = sum(int(x) for x in generic)
        symbols = re.findall(r'\{([^0-9])\}', front_cost)
        return generic_sum + len(symbols)

    @staticmethod
    def parse_stat(val):
        try: return int(pd.to_numeric(val, errors='coerce'))
        except: return 0

    @staticmethod
    def extraer_colores(val):
        if not val or pd.isna(val) or val == "" or val == "[]": return set()
        if isinstance(val, list): return set(val)
        s = str(val).replace("[","").replace("]","").replace("'","").replace('"',"").replace(","," ")
        return {c.strip().upper() for c in s.split() if c.strip().upper() in 'WUBRG'}

    def prepare_collection(self, df):
        if df.empty: return df
        df['mana_value'] = df['mana_cost'].apply(self.calculate_mana_value)
        df['power_num'] = df['power'].apply(self.parse_stat)
        
        return df.groupby('name_clean').agg({
            'name': 'first', 'set_name': 'first', 'rarity': 'first',
            'layout': 'first',
            'type_line': 'first', 'cantidad': 'sum', 'oracle_text': 'first',
            'color_identity': 'first', 'mana_cost': 'first', 
            'mana_value': 'first', 'power_num': 'first'
        }).reset_index()

    def filter_cards(self, df, name="", type_line="", rarities=None, sets=None):
        res = df.copy()
        if name: res = res[res['name'].str.contains(name, case=False, na=False)]
        if type_line: res = res[res['type_line'].str.contains(type_line, case=False, na=False)]
        if rarities: res = res[res['rarity'].isin(rarities)]
        if sets: res = res[res['set_name'].isin(sets)]
        return res

    def is_legal_in_commander(self, row, cmd_colors_set):
        try:
            card_colors = self.extraer_colores(row['color_identity'])
            if not card_colors.issubset(cmd_colors_set): return False
            
            if pd.notna(row['mana_cost']) and row['mana_cost'] != '':
                symbols = re.findall(r'\{([WUBRG])\}', str(row['mana_cost']).upper())
                if any(s not in cmd_colors_set for s in symbols): return False

            text = str(row['oracle_text']).upper()
            for forbidden in {'W', 'U', 'B', 'R', 'G'} - cmd_colors_set:
                if f"{{{forbidden}}}" in text: return False
            return True
        except: return False

    def generate_deck(self, full_df, name_filter, type_filter, rarity_filter, set_filter):
        # 1. Selector de Comandante
        cmd_pool = self.filter_cards(full_df, name_filter, type_filter, rarity_filter, set_filter)
        potential_commanders = cmd_pool[cmd_pool['type_line'].str.contains("Legendary Creature", case=False, na=False)]
        
        if potential_commanders.empty:
            return None, "No se encontró una Criatura Legendaria válida."

        commander = potential_commanders.iloc[0]
        cmd_colors = self.extraer_colores(commander['color_identity'])
        
        # 2. Pool Legal
        legal_pool = full_df[full_df.apply(lambda r: self.is_legal_in_commander(r, cmd_colors), axis=1)].copy()
        legal_pool = legal_pool[legal_pool['name_clean'] != commander['name_clean']]
        
        # 3. Sinergia y Puntuación
        utilidades = {
            "ramp": ["mana", "search", "library", "land", "battlefield", "treasure", "rock"],
            "draw": ["draw", "discard", "scry", "look", "top", "reveal"],
            "removal": ["destroy", "exile", "damage", "sacrifice", "counter"],
            "protection": ["prevent", "hexproof", "indestructible", "protection", "ward", "combat", "unblockable"]
        }
        util_keys = [k for v in utilidades.values() for k in v]
        
        tema = type_filter if type_filter else name_filter

        def score_card(row):
            text = (str(row['oracle_text']) + " " + str(row['name']) + " " + str(row['type_line'])).lower()
            score = 0
            if row['cantidad'] > 0: score += 50
            if tema and tema.lower() in text: score += 30
            score += sum(5 for k in util_keys if k in text)
            if row['mana_value'] > 5: score -= (row['mana_value'] - 5) * 8
            return score

        legal_pool['score'] = legal_pool.apply(score_card, axis=1)
        
        # 4. Construcción equilibrada
        is_land = legal_pool['type_line'].str.contains("Land", case=False, na=False)
        lands = legal_pool[is_land].sort_values('score', ascending=False).head(36)
        spells_pool = legal_pool[~is_land].copy()
        
        # Aplicar filtros solo a hechizos para permitir tierras de otros sets
        if set_filter: spells_pool = spells_pool[spells_pool['set_name'].isin(set_filter)]
        if rarity_filter: spells_pool = spells_pool[spells_pool['rarity'].isin(rarity_filter)]
        
        spells_pool = spells_pool.sort_values('score', ascending=False)
        
        deck = [commander.to_dict()]
        deck.extend(lands.to_dict('records'))
        
        objetivos = {'Creature': 25, 'Artifact': 14, 'Enchantment': 8, 'Instant': 8, 'Sorcery': 7}
        nombres_en_mazo = {c['name_clean'] for c in deck}

        for tipo, meta in objetivos.items():
            candidatos = spells_pool[
                (spells_pool['type_line'].str.contains(tipo, case=False, na=False)) & 
                (~spells_pool['name_clean'].isin(nombres_en_mazo))
            ].head(meta)
            deck.extend(candidatos.to_dict('records'))
            nombres_en_mazo.update(candidatos['name_clean'].tolist())

        # Relleno
        faltantes = 100 - len(deck)
        if faltantes > 0:
            pool_restante = spells_pool[~spells_pool['name_clean'].isin(nombres_en_mazo)].head(faltantes)
            deck.extend(pool_restante.to_dict('records'))

        df_deck = pd.DataFrame(deck)
        
        # Ordenar visualización
        df_deck['viz_priority'] = df_deck['type_line'].apply(lambda x: 2 if "Land" in str(x) else 1)
        df_deck.loc[df_deck['name_clean'] == commander['name_clean'], 'viz_priority'] = 0
        df_deck = df_deck.sort_values(by=['viz_priority', 'mana_value', 'power_num'], ascending=[True, False, False])
        
        return df_deck, f"Comandante: {commander['name']}"