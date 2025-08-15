import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime, timedelta

class TradingAlgorithm(ABC):
    """Classe de base pour tous les algorithmes de trading"""
    
    def __init__(self, parameters: Dict):
        self.parameters = parameters
    
    @abstractmethod
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        """
        Calcule les signaux d'achat/vente basés sur l'algorithme
        
        Args:
            price_data: Liste de dictionnaires avec 'date', 'open', 'high', 'low', 'close', 'volume'
            
        Returns:
            Dict avec 'signal' ('BUY', 'SELL', 'HOLD'), 'strength' (0-1), 'reason'
        """
        pass
    
    def _get_prices(self, price_data: List[Dict]) -> np.ndarray:
        """Extrait les prix de fermeture des données"""
        return np.array([float(candle['close']) for candle in price_data])
    
    def _get_volumes(self, price_data: List[Dict]) -> np.ndarray:
        """Extrait les volumes des données"""
        return np.array([float(candle.get('volume', 0)) for candle in price_data])

class ThresholdAlgorithm(TradingAlgorithm):
    """Algorithme de seuils avec gestion de position cible : Acheter en dessous de X1, vendre au-dessus de X2"""
    
    def __init__(self, parameters: Dict, strategy=None):
        super().__init__(parameters)
        self.strategy = strategy  # Référence vers la stratégie pour accéder aux quantités cibles
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 1:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        current_price = float(price_data[-1]['close'])
        threshold_low = self.parameters.get('threshold_low', 0)
        threshold_high = self.parameters.get('threshold_high', float('inf'))
        
        # Récupérer les quantités cibles si la stratégie est disponible
        target_min_quantity = getattr(self.strategy, 'target_min_quantity', 0) if self.strategy else 0
        target_max_quantity = getattr(self.strategy, 'target_max_quantity', 0) if self.strategy else 0
        portfolio_quantity = getattr(self.strategy, 'portfolio_quantity', -1) if self.strategy else -1
        
        # Logique de gestion des positions cibles avec calcul automatique des quantités
        if current_price <= threshold_low:
            # Signal d'achat si on peut augmenter la position
            if target_max_quantity > 0 and portfolio_quantity >= 0:
                if portfolio_quantity < target_max_quantity:
                    # Calculer la quantité à acheter automatiquement
                    quantity_to_buy = target_max_quantity - portfolio_quantity
                    # Limiter par la limite de sécurité depuis les paramètres
                    max_trade_size = float(self.parameters.get('order_size', 1000))
                    final_quantity = min(quantity_to_buy, max_trade_size)
                    
                    strength = min(1.0, (threshold_low - current_price) / threshold_low * 2)
                    return {
                        'signal': 'BUY',
                        'strength': strength,
                        'reason': f'Prix ({current_price}) en dessous du seuil bas ({threshold_low}) - Acheter {final_quantity} pour atteindre {target_max_quantity}',
                        'auto_quantity': True,
                        'calculated_quantity': final_quantity
                    }
                else:
                    return {
                        'signal': 'HOLD',
                        'strength': 0.0,
                        'reason': f'Position déjà au maximum ({portfolio_quantity}/{target_max_quantity})'
                    }
            else:
                # Comportement classique si pas de quantités cibles
                strength = min(1.0, (threshold_low - current_price) / threshold_low * 2)
                return {
                    'signal': 'BUY',
                    'strength': strength,
                    'reason': f'Prix ({current_price}) en dessous du seuil bas ({threshold_low})'
                }
        
        elif current_price >= threshold_high:
            # Signal de vente si on peut réduire la position
            if target_min_quantity > 0 and portfolio_quantity >= 0:
                if portfolio_quantity > target_min_quantity:
                    # Calculer la quantité à vendre automatiquement
                    quantity_to_sell = portfolio_quantity - target_min_quantity
                    # Limiter par la limite de sécurité depuis les paramètres
                    max_trade_size = float(self.parameters.get('order_size', 1000))
                    final_quantity = min(quantity_to_sell, max_trade_size)
                    
                    strength = min(1.0, (current_price - threshold_high) / threshold_high * 2)
                    return {
                        'signal': 'SELL',
                        'strength': strength,
                        'reason': f'Prix ({current_price}) au-dessus du seuil haut ({threshold_high}) - Vendre {final_quantity} pour atteindre {target_min_quantity}',
                        'auto_quantity': True,
                        'calculated_quantity': final_quantity
                    }
                else:
                    return {
                        'signal': 'HOLD',
                        'strength': 0.0,
                        'reason': f'Position déjà au minimum ({portfolio_quantity}/{target_min_quantity})'
                    }
            else:
                # Comportement classique si pas de quantités cibles
                strength = min(1.0, (current_price - threshold_high) / threshold_high * 2)
                return {
                    'signal': 'SELL',
                    'strength': strength,
                    'reason': f'Prix ({current_price}) au-dessus du seuil haut ({threshold_high})'
                }
        else:
            return {
                'signal': 'HOLD',
                'strength': 0.0,
                'reason': f'Prix ({current_price}) dans la zone neutre'
            }

class MovingAverageCrossoverAlgorithm(TradingAlgorithm):
    """Algorithme de croisement de moyennes mobiles"""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 50:  # Besoin d'au moins 50 points pour les MA
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        prices = self._get_prices(price_data)
        ma1_period = self.parameters.get('ma1_period', 20)
        ma2_period = self.parameters.get('ma2_period', 50)
        
        if len(prices) < max(ma1_period, ma2_period):
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données pour les MA'}
        
        # Calculer les moyennes mobiles
        ma1 = np.mean(prices[-ma1_period:])
        ma2 = np.mean(prices[-ma2_period:])
        
        # Calculer les MA précédentes pour détecter le croisement
        if len(prices) >= max(ma1_period, ma2_period) + 1:
            ma1_prev = np.mean(prices[-ma1_period-1:-1])
            ma2_prev = np.mean(prices[-ma2_period-1:-1])
            
            # Détecter le croisement
            if ma1 > ma2 and ma1_prev <= ma2_prev:
                return {
                    'signal': 'BUY',
                    'strength': min(1.0, abs(ma1 - ma2) / ma2),
                    'reason': f'Croisement haussier: MA{ma1_period} ({ma1:.2f}) > MA{ma2_period} ({ma2:.2f})'
                }
            elif ma1 < ma2 and ma1_prev >= ma2_prev:
                return {
                    'signal': 'SELL',
                    'strength': min(1.0, abs(ma2 - ma1) / ma2),
                    'reason': f'Croisement baissier: MA{ma1_period} ({ma1:.2f}) < MA{ma2_period} ({ma2:.2f})'
                }
        
        # Pas de croisement, signal basé sur la position relative
        if ma1 > ma2:
            strength = min(1.0, abs(ma1 - ma2) / ma2)
            return {
                'signal': 'HOLD',
                'strength': strength * 0.5,  # Signal plus faible
                'reason': f'MA{ma1_period} ({ma1:.2f}) > MA{ma2_period} ({ma2:.2f}) - tendance haussière'
            }
        else:
            strength = min(1.0, abs(ma2 - ma1) / ma2)
            return {
                'signal': 'HOLD',
                'strength': strength * 0.5,
                'reason': f'MA{ma1_period} ({ma1:.2f}) < MA{ma2_period} ({ma2:.2f}) - tendance baissière'
            }

class RSIAlgorithm(TradingAlgorithm):
    """Algorithme RSI (Relative Strength Index)"""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 30:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        prices = self._get_prices(price_data)
        rsi_period = self.parameters.get('rsi_period', 14)
        rsi_low = self.parameters.get('rsi_low', 30)
        rsi_high = self.parameters.get('rsi_high', 70)
        
        if len(prices) < rsi_period + 1:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données pour RSI'}
        
        # Calculer le RSI
        rsi = self._calculate_rsi(prices, rsi_period)
        
        if rsi <= rsi_low:
            strength = min(1.0, (rsi_low - rsi) / rsi_low)
            return {
                'signal': 'BUY',
                'strength': strength,
                'reason': f'RSI ({rsi:.2f}) en survente (seuil: {rsi_low})'
            }
        elif rsi >= rsi_high:
            strength = min(1.0, (rsi - rsi_high) / (100 - rsi_high))
            return {
                'signal': 'SELL',
                'strength': strength,
                'reason': f'RSI ({rsi:.2f}) en surachat (seuil: {rsi_high})'
            }
        else:
            return {
                'signal': 'HOLD',
                'strength': 0.0,
                'reason': f'RSI ({rsi:.2f}) dans la zone neutre'
            }
    
    def _calculate_rsi(self, prices: np.ndarray, period: int) -> float:
        """Calcule le RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        # Calculer les variations
        deltas = np.diff(prices)
        
        # Séparer les gains et pertes
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Moyennes mobiles des gains et pertes
        avg_gains = np.mean(gains[-period:])
        avg_losses = np.mean(losses[-period:])
        
        if avg_losses == 0:
            return 100.0
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

class BollingerBandsAlgorithm(TradingAlgorithm):
    """Algorithme des bandes de Bollinger"""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 20:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        prices = self._get_prices(price_data)
        bb_period = self.parameters.get('bb_period', 20)
        bb_std = self.parameters.get('bb_std', 2.0)
        
        if len(prices) < bb_period:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données pour Bollinger'}
        
        # Calculer les bandes de Bollinger
        sma = np.mean(prices[-bb_period:])
        std = np.std(prices[-bb_period:])
        
        upper_band = sma + (bb_std * std)
        lower_band = sma - (bb_std * std)
        
        current_price = prices[-1]
        
        # Calculer la position relative dans les bandes
        band_width = upper_band - lower_band
        if band_width == 0:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Bandes de Bollinger trop étroites'}
        
        position = (current_price - lower_band) / band_width
        
        if current_price <= lower_band:
            strength = min(1.0, (lower_band - current_price) / lower_band)
            return {
                'signal': 'BUY',
                'strength': strength,
                'reason': f'Prix ({current_price:.2f}) touche la bande basse ({lower_band:.2f})'
            }
        elif current_price >= upper_band:
            strength = min(1.0, (current_price - upper_band) / upper_band)
            return {
                'signal': 'SELL',
                'strength': strength,
                'reason': f'Prix ({current_price:.2f}) touche la bande haute ({upper_band:.2f})'
            }
        else:
            # Signal basé sur la position dans les bandes
            if position < 0.2:  # Proche de la bande basse
                return {
                    'signal': 'HOLD',
                    'strength': 0.3,
                    'reason': f'Prix ({current_price:.2f}) proche de la bande basse'
                }
            elif position > 0.8:  # Proche de la bande haute
                return {
                    'signal': 'HOLD',
                    'strength': 0.3,
                    'reason': f'Prix ({current_price:.2f}) proche de la bande haute'
                }
            else:
                return {
                    'signal': 'HOLD',
                    'strength': 0.0,
                    'reason': f'Prix ({current_price:.2f}) dans la zone centrale'
                }

class MACDAlgorithm(TradingAlgorithm):
    """Algorithme MACD (Moving Average Convergence Divergence)"""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 50:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        prices = self._get_prices(price_data)
        macd_fast = self.parameters.get('macd_fast', 12)
        macd_slow = self.parameters.get('macd_slow', 26)
        macd_signal = self.parameters.get('macd_signal', 9)
        
        if len(prices) < macd_slow + macd_signal:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données pour MACD'}
        
        # Calculer MACD
        ema_fast = self._calculate_ema(prices, macd_fast)
        ema_slow = self._calculate_ema(prices, macd_slow)
        macd_line = ema_fast - ema_slow
        
        # Calculer la ligne de signal (EMA du MACD)
        macd_values = []
        for i in range(macd_slow, len(prices)):
            ema_fast_i = self._calculate_ema(prices[:i+1], macd_fast)
            ema_slow_i = self._calculate_ema(prices[:i+1], macd_slow)
            macd_values.append(ema_fast_i - ema_slow_i)
        
        if len(macd_values) < macd_signal:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données pour signal MACD'}
        
        signal_line = self._calculate_ema(np.array(macd_values), macd_signal)
        histogram = macd_line - signal_line
        
        # Détecter les croisements
        if len(macd_values) >= 2:
            prev_macd = macd_values[-2]
            prev_signal = self._calculate_ema(np.array(macd_values[:-1]), macd_signal)
            
            if macd_line > signal_line and prev_macd <= prev_signal:
                strength = min(1.0, abs(macd_line - signal_line) / abs(signal_line))
                return {
                    'signal': 'BUY',
                    'strength': strength,
                    'reason': f'MACD ({macd_line:.4f}) croise au-dessus du signal ({signal_line:.4f})'
                }
            elif macd_line < signal_line and prev_macd >= prev_signal:
                strength = min(1.0, abs(signal_line - macd_line) / abs(signal_line))
                return {
                    'signal': 'SELL',
                    'strength': strength,
                    'reason': f'MACD ({macd_line:.4f}) croise en-dessous du signal ({signal_line:.4f})'
                }
        
        # Signal basé sur la position relative
        if macd_line > signal_line:
            strength = min(1.0, abs(macd_line - signal_line) / abs(signal_line))
            return {
                'signal': 'HOLD',
                'strength': strength * 0.5,
                'reason': f'MACD ({macd_line:.4f}) > Signal ({signal_line:.4f}) - tendance haussière'
            }
        else:
            strength = min(1.0, abs(signal_line - macd_line) / abs(signal_line))
            return {
                'signal': 'HOLD',
                'strength': strength * 0.5,
                'reason': f'MACD ({macd_line:.4f}) < Signal ({signal_line:.4f}) - tendance baissière'
            }
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calcule l'EMA (Exponential Moving Average)"""
        if len(prices) < period:
            return np.mean(prices)
        
        alpha = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return ema

class GridTradingAlgorithm(TradingAlgorithm):
    """Algorithme de Grid Trading"""
    
    def calculate_signals(self, price_data: List[Dict]) -> Dict:
        if len(price_data) < 1:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Pas assez de données'}
        
        current_price = float(price_data[-1]['close'])
        grid_min = self.parameters.get('grid_min', 0)
        grid_max = self.parameters.get('grid_max', float('inf'))
        grid_levels = self.parameters.get('grid_levels', 10)
        
        if grid_max <= grid_min:
            return {'signal': 'HOLD', 'strength': 0.0, 'reason': 'Paramètres de grille invalides'}
        
        # Calculer les niveaux de la grille
        grid_step = (grid_max - grid_min) / grid_levels
        grid_levels_list = [grid_min + i * grid_step for i in range(grid_levels + 1)]
        
        # Trouver le niveau le plus proche
        closest_level = min(grid_levels_list, key=lambda x: abs(x - current_price))
        
        # Déterminer le signal basé sur la position par rapport au niveau
        if current_price <= closest_level + grid_step * 0.1:  # Proche du niveau inférieur
            strength = min(1.0, abs(closest_level - current_price) / grid_step)
            return {
                'signal': 'BUY',
                'strength': strength,
                'reason': f'Prix ({current_price:.2f}) proche du niveau d\'achat ({closest_level:.2f})'
            }
        elif current_price >= closest_level - grid_step * 0.1:  # Proche du niveau supérieur
            strength = min(1.0, abs(current_price - closest_level) / grid_step)
            return {
                'signal': 'SELL',
                'strength': strength,
                'reason': f'Prix ({current_price:.2f}) proche du niveau de vente ({closest_level:.2f})'
            }
        else:
            return {
                'signal': 'HOLD',
                'strength': 0.0,
                'reason': f'Prix ({current_price:.2f}) entre les niveaux de la grille'
            }

class AlgorithmFactory:
    """Factory pour créer les instances d'algorithmes"""
    
    _algorithms = {
        'threshold': ThresholdAlgorithm,
        'ma_crossover': MovingAverageCrossoverAlgorithm,
        'rsi': RSIAlgorithm,
        'bollinger': BollingerBandsAlgorithm,
        'macd': MACDAlgorithm,
        'grid': GridTradingAlgorithm,
    }
    
    @classmethod
    def create_algorithm(cls, algorithm_type: str, parameters: Dict, strategy=None) -> TradingAlgorithm:
        """Crée une instance de l'algorithme spécifié"""
        if algorithm_type not in cls._algorithms:
            raise ValueError(f'Algorithme non supporté: {algorithm_type}')
        
        algorithm_class = cls._algorithms[algorithm_type]
        
        # Pour l'algorithme Threshold, passer la stratégie pour accéder aux quantités cibles
        if algorithm_type == 'threshold':
            return algorithm_class(parameters, strategy)
        else:
            return algorithm_class(parameters)
    
    @classmethod
    def get_algorithm_parameters(cls, algorithm_type: str) -> Dict:
        """Retourne les paramètres par défaut pour un algorithme"""
        default_params = {
            'threshold': {
                'threshold_low': 100.0,
                'threshold_high': 200.0,
                'order_size': 1.0,
                'stop_loss': 0.05
            },
            'ma_crossover': {
                'ma1_period': 20,
                'ma2_period': 50,
                'order_size': 1.0,
                'stop_loss': 0.05
            },
            'rsi': {
                'rsi_period': 14,
                'rsi_low': 30,
                'rsi_high': 70,
                'order_size': 1.0,
                'stop_loss': 0.05
            },
            'bollinger': {
                'bb_period': 20,
                'bb_std': 2.0,
                'order_size': 1.0,
                'stop_loss': 0.05
            },
            'macd': {
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                'order_size': 1.0,
                'stop_loss': 0.05
            },
            'grid': {
                'grid_min': 100.0,
                'grid_max': 200.0,
                'grid_levels': 10,
                'order_size': 1.0,
                'stop_loss': 0.05
            }
        }
        
        return default_params.get(algorithm_type, {}) 