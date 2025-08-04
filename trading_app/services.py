"""
Services pour gérer les interactions avec les courtiers
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.contrib.auth.models import User
from .brokers.factory import BrokerFactory
from .models import BrokerCredentials, Asset, Trade, Position, AssetTradable, AssetType, Market, AllAssets


class BrokerService:
    """Service pour gérer les interactions avec les courtiers"""
    
    def __init__(self, user: User):
        self.user = user
    
    def get_user_brokers(self) -> List[BrokerCredentials]:
        """Récupérer tous les courtiers configurés pour l'utilisateur"""
        return BrokerCredentials.objects.filter(user=self.user, is_active=True)
    
    def get_broker_instance(self, broker_credentials: BrokerCredentials):
        """Créer une instance de courtier à partir des credentials"""
        credentials_dict = broker_credentials.get_credentials_dict()
        return BrokerFactory.create_broker(
            broker_credentials.broker_type,
            self.user,
            credentials_dict
        )
    
    def sync_positions_from_broker(self, broker_credentials: BrokerCredentials) -> List[Position]:
        """Synchronise les positions depuis un broker"""
        print(f"🔄 Synchronisation des positions depuis {broker_credentials.broker_type}")
        
        try:
            # Créer le broker
            broker = self.get_broker_instance(broker_credentials)
            
            # Récupérer les positions
            positions_data = broker.get_positions()
            print(f"📊 {len(positions_data)} positions récupérées")
            
            positions = []
            for i, pos_data in enumerate(positions_data):
                try:
                    # Gestion spéciale pour Binance
                    if broker_credentials.broker_type == 'binance':
                        # Binance retourne des balances avec asset, free, locked, total
                        asset_symbol = pos_data.get('asset', 'N/A')
                        position_size = float(pos_data.get('total', 0))
                        
                        if position_size <= 0:
                            continue  # Ignorer les balances nulles
                        
                        # Récupérer ou créer AssetType et Market pour Binance
                        asset_type, _ = AssetType.objects.get_or_create(name='Crypto')
                        market, _ = Market.objects.get_or_create(name='Binance')
                        
                        # Récupérer ou créer l'Asset sous-jacent
                        asset, _ = Asset.objects.get_or_create(
                            symbol=asset_symbol,
                            defaults={
                                'name': asset_symbol,
                                'sector': 'Cryptocurrency',
                                'industry': 'Digital Assets',
                                'market_cap': 0.0,
                                'price_history': 'xxxx',
                            }
                        )
                        
                        # Trouver un AllAssets correspondant existant
                        all_asset = AssetTradable.find_matching_all_asset(asset_symbol, 'binance')
                        
                        if not all_asset:
                            # Debug : afficher les symboles disponibles pour Binance
                            available_symbols = AllAssets.objects.filter(platform='binance').values_list('symbol', flat=True)
                            print(f"⚠️ Aucun AllAssets trouvé pour {asset_symbol}")
                            print(f"📋 Symboles disponibles pour Binance: {list(available_symbols)}")
                            continue
                        
                        # Récupérer ou créer l'AssetTradable
                        asset_tradable, _ = AssetTradable.objects.get_or_create(
                            symbol=asset_symbol.upper(),
                            platform='binance',
                            defaults={
                                'all_asset': all_asset,
                                'name': asset_symbol,
                                'asset_type': asset_type,
                                'market': market,
                            }
                        )
                        
                        # Récupérer ou créer la Position
                        position, created = Position.objects.get_or_create(
                            user=broker_credentials.user,
                            asset_tradable=asset_tradable,
                            defaults={
                                'size': Decimal(str(position_size)),
                                'entry_price': Decimal('0.0'),  # Pas de prix d'entrée pour les balances
                                'current_price': Decimal('0.0'),  # À récupérer si nécessaire
                                'side': 'BUY',  # Par défaut pour les balances
                                'status': 'OPEN',
                                'pnl': Decimal('0.0'),
                            }
                        )
                        
                        if not created:
                            # Mise à jour si la position existe déjà
                            position.size = Decimal(str(position_size))
                            position.save()
                        
                        positions.append(position)
                        print(f"✅ Position Binance synchronisée: {asset_symbol} {position_size}")
                        
                    else:
                        # Gestion pour les autres brokers (Saxo, etc.)
                        # Récupérer ou créer AssetType et Market
                        asset_type, _ = AssetType.objects.get_or_create(name=pos_data.get('type', 'Unknown'))
                        market, _ = Market.objects.get_or_create(name=pos_data.get('market', 'Unknown'))
                        
                        # Pour Saxo, créer un Asset unique pour chaque position
                        # en ajoutant un suffixe basé sur l'index pour éviter les conflits
                        unique_symbol = f"{pos_data['symbol']}_{i}" if broker_credentials.broker_type == 'saxo' else pos_data['symbol']
                        
                        # Récupérer ou créer l'Asset sous-jacent avec le symbole unique
                        asset, _ = Asset.objects.get_or_create(
                            symbol=unique_symbol,
                            defaults={
                                'name': pos_data.get('name', pos_data['symbol']),
                                'sector': pos_data.get('sector', 'xxxx'),
                                'industry': pos_data.get('industry', 'xxxx'),
                                'market_cap': pos_data.get('market_cap', 0.0),
                                'price_history': pos_data.get('price_history', 'xxxx'),
                            }
                        )
                        
                        # Pour Saxo, créer un AssetTradable unique pour chaque position
                        # en ajoutant un suffixe basé sur l'index
                        unique_symbol = f"{pos_data['symbol']}_{i}" if broker_credentials.broker_type == 'saxo' else pos_data['symbol']
                        
                        # Trouver un AllAssets correspondant existant (utiliser le symbole original)
                        original_symbol = pos_data['symbol']
                        all_asset = AssetTradable.find_matching_all_asset(original_symbol, broker_credentials.broker_type)
                        
                        if not all_asset:
                            print(f"⚠️ Aucun AllAssets trouvé pour {original_symbol}, position ignorée")
                            continue
                        
                        # Pour Saxo, créer un AssetTradable unique avec suffixe pour chaque position
                        if broker_credentials.broker_type == 'saxo':
                            # Créer un AssetTradable unique avec le suffixe
                            asset_tradable, _ = AssetTradable.objects.get_or_create(
                                symbol=unique_symbol.upper(),
                                platform=broker_credentials.broker_type,
                                defaults={
                                    'all_asset': all_asset,
                                    'name': pos_data.get('name', original_symbol),
                                    'asset_type': asset_type,
                                    'market': market,
                                }
                            )
                            
                            # Créer une nouvelle position (pas get_or_create car on veut des positions multiples)
                            position = Position.objects.create(
                                user=broker_credentials.user,
                                asset_tradable=asset_tradable,
                                size=Decimal(str(pos_data.get('size', 0))),
                                entry_price=Decimal(str(pos_data.get('entry_price', 0))),
                                current_price=Decimal(str(pos_data.get('current_price', 0))),
                                side=pos_data.get('side', 'BUY'),
                                status=pos_data.get('status', 'OPEN'),
                                pnl=Decimal(str(pos_data.get('pnl', 0))),
                            )
                        else:
                            # Pour les autres brokers, utiliser la logique existante
                            asset_tradable, _ = AssetTradable.objects.get_or_create(
                                symbol=original_symbol.upper(),
                                platform=broker_credentials.broker_type,
                                defaults={
                                    'all_asset': all_asset,
                                    'name': pos_data.get('name', original_symbol),
                                    'asset_type': asset_type,
                                    'market': market,
                                }
                            )
                            
                            # Récupérer ou créer la Position
                            position, created = Position.objects.get_or_create(
                                user=broker_credentials.user,
                                asset_tradable=asset_tradable,
                                defaults={
                                    'size': Decimal(str(pos_data.get('size', 0))),
                                    'entry_price': Decimal(str(pos_data.get('entry_price', 0))),
                                    'current_price': Decimal(str(pos_data.get('current_price', 0))),
                                    'side': pos_data.get('side', 'BUY'),
                                    'status': pos_data.get('status', 'OPEN'),
                                    'pnl': Decimal(str(pos_data.get('pnl', 0))),
                                }
                            )
                        
                        # Pour Saxo, on ne fait pas de mise à jour car on crée toujours de nouvelles positions
                        # Pour les autres brokers, mettre à jour si la position existe déjà
                        if broker_credentials.broker_type != 'saxo' and not created:
                            position.size = Decimal(str(pos_data.get('size', 0)))
                            position.entry_price = Decimal(str(pos_data.get('entry_price', 0)))
                            position.current_price = Decimal(str(pos_data.get('current_price', 0)))
                            position.side = pos_data.get('side', 'BUY')
                            position.status = pos_data.get('status', 'OPEN')
                            position.pnl = Decimal(str(pos_data.get('pnl', 0)))
                            position.save()
                        
                        positions.append(position)
                        
                except Exception as e:
                    print(f"❌ Erreur traitement position {pos_data}: {e}")
                    continue
            
            print(f"✅ {len(positions)} positions synchronisées avec succès")
            return positions
            
        except Exception as e:
            print(f"❌ Erreur synchronisation positions: {e}")
            return []
    
    def sync_trades_from_broker(self, broker_credentials: BrokerCredentials, limit: int = 100) -> Dict[str, Any]:
        """Synchronise les trades depuis un broker et retourne un dictionnaire avec les résultats"""
        print(f"🔄 Synchronisation des trades depuis {broker_credentials.broker_type}")
        
        try:
            # Créer le broker
            broker = self.get_broker_instance(broker_credentials)
            
            # Récupérer les trades
            trades_data = broker.get_trades(limit)
            print(f"📊 {len(trades_data)} trades récupérés")
            
            trades = []
            saved_count = 0
            for i, trade_data in enumerate(trades_data):
                try:
                    # Récupérer ou créer AssetType et Market
                    asset_type, _ = AssetType.objects.get_or_create(name=trade_data.get('type', 'Unknown'))
                    market, _ = Market.objects.get_or_create(name=trade_data.get('market', 'Unknown'))
                    
                    # Pour Saxo, créer un Asset unique pour chaque trade
                    # en ajoutant un suffixe basé sur l'index pour éviter les conflits
                    unique_symbol = f"{trade_data['symbol']}_{i}" if broker_credentials.broker_type == 'saxo' else trade_data['symbol']
                    
                    # Récupérer ou créer l'Asset sous-jacent avec le symbole unique
                    asset, _ = Asset.objects.get_or_create(
                        symbol=unique_symbol,
                        defaults={
                            'name': trade_data.get('name', trade_data['symbol']),
                            'sector': trade_data.get('sector', 'xxxx'),
                            'industry': trade_data.get('industry', 'xxxx'),
                            'market_cap': trade_data.get('market_cap', 0.0),
                            'price_history': trade_data.get('price_history', 'xxxx'),
                        }
                    )
                    
                    # Trouver un AllAssets correspondant existant (utiliser le symbole original)
                    original_symbol = trade_data['symbol']
                    all_asset = AssetTradable.find_matching_all_asset(original_symbol, broker_credentials.broker_type)
                    
                    if not all_asset:
                        # Debug : afficher les symboles disponibles
                        available_symbols = AllAssets.objects.filter(platform=broker_credentials.broker_type).values_list('symbol', flat=True)
                        print(f"⚠️ Aucun AllAssets trouvé pour {original_symbol}")
                        print(f"📋 Symboles disponibles pour {broker_credentials.broker_type}: {list(available_symbols)}")
                        continue
                    
                    # Récupérer ou créer l'AssetTradable (utiliser le symbole original)
                    asset_tradable, _ = AssetTradable.objects.get_or_create(
                        symbol=original_symbol.upper(),
                        platform=broker_credentials.broker_type,
                        defaults={
                            'all_asset': all_asset,
                            'name': trade_data.get('name', original_symbol),
                            'asset_type': asset_type,
                            'market': market,
                        }
                    )
                    
                    # Récupérer ou créer le Trade
                    trade, created = Trade.objects.get_or_create(
                        user=broker_credentials.user,
                        asset_tradable=asset_tradable,
                        timestamp=trade_data.get('timestamp'),
                        defaults={
                            'size': Decimal(str(trade_data.get('size', 0))),
                            'price': Decimal(str(trade_data.get('price', 0))),
                            'side': trade_data.get('side', 'BUY'),
                            'platform': broker_credentials.broker_type,
                        }
                    )
                    
                    if created:
                        saved_count += 1
                    else:
                        # Mise à jour si le trade existe déjà
                        trade.size = Decimal(str(trade_data.get('size', 0)))
                        trade.price = Decimal(str(trade_data.get('price', 0)))
                        trade.side = trade_data.get('side', 'BUY')
                        trade.platform = broker_credentials.broker_type
                        trade.save()
                    
                    trades.append(trade)
                    print(f"✅ Trade synchronisé: {trade.asset_tradable.symbol}")
                    
                except Exception as e:
                    print(f"❌ Erreur lors de la synchronisation du trade {trade_data.get('symbol', 'Unknown')}: {e}")
                    continue
            
            # Compter le nombre total de trades pour ce broker
            total_trades = Trade.objects.filter(
                user=broker_credentials.user,
                platform=broker_credentials.broker_type
            ).count()
            
            print(f"✅ Synchronisation terminée: {len(trades)} trades traités, {saved_count} nouveaux")
            return {
                'success': True,
                'trades': trades,
                'saved_count': saved_count,
                'total_trades': total_trades,
                'message': f"Synchronisation réussie: {saved_count} nouveaux trades ajoutés"
            }
            
        except Exception as e:
            print(f"❌ Erreur de synchronisation: {e}")
            return {
                'success': False,
                'error': str(e),
                'trades': [],
                'saved_count': 0,
                'total_trades': 0
            }
    
    def _process_broker_trade(self, broker_trade, broker_credentials, symbol=None):
        """Process a single broker trade and return created Trade objects"""
        created_trades = []
        
        try:
            # Determine the symbol from the trade data or parameter
            trade_symbol = symbol or broker_trade.get('symbol', 'UNKNOWN')
            print(f"  Traitement trade pour symbole: {trade_symbol}")
            
            # Create or retrieve the asset_tradable
            # First, try to find existing AllAssets
            all_asset, _ = AllAssets.objects.get_or_create(
                symbol=trade_symbol,
                platform=broker_credentials.broker_type,
                defaults={
                    'name': trade_symbol,
                    'asset_type': 'Crypto' if broker_credentials.broker_type == 'binance' else 'Stock',
                    'market': 'SPOT' if broker_credentials.broker_type == 'binance' else 'NASDAQ',
                    'currency': 'USD',
                }
            )
            
            # Then create or get AssetTradable
            asset_tradable, _ = AssetTradable.objects.get_or_create(
                all_asset=all_asset,
                defaults={
                    'symbol': trade_symbol,
                    'name': trade_symbol,
                    'platform': broker_credentials.broker_type,
                    'asset_type': AssetType.objects.get_or_create(name='Crypto' if broker_credentials.broker_type == 'binance' else 'Stock')[0],
                    'market': Market.objects.get_or_create(name='SPOT' if broker_credentials.broker_type == 'binance' else 'NASDAQ')[0],
                }
            )
            
            # Determine side from Binance format or other formats
            side = 'BUY'
            if broker_credentials.broker_type == 'binance':
                side = 'BUY' if broker_trade.get('isBuyer', True) else 'SELL'
            else:
                side = broker_trade.get('side', 'BUY')
            
            # Create the trade
            trade = Trade.objects.create(
                user=self.user,
                asset_tradable=asset_tradable,
                size=Decimal(str(broker_trade.get('qty', broker_trade.get('size', 0)))),
                price=Decimal(str(broker_trade.get('price', 0))),
                side=side,
                platform=broker_credentials.broker_type.upper(),
            )
            
            created_trades.append(trade)
            print(f"    Trade créé: {trade.id} - {side} {trade.size} @ {trade.price}")
            
        except Exception as e:
            print(f"    Erreur lors du traitement du trade: {e}")
            print(f"    Données du trade: {broker_trade}")
        
        return created_trades
    
    def place_order(self, broker_credentials: BrokerCredentials, symbol: str, 
                   side: str, size: Decimal, order_type: str = "MARKET", 
                   price: Optional[Decimal] = None) -> Dict[str, Any]:
        """Placer un ordre via un courtier"""
        broker = self.get_broker_instance(broker_credentials)
        
        if not broker.authenticate():
            return {"error": "Échec de l'authentification"}
        
        return broker.place_order(symbol, side, size, order_type, price)
    
    def get_asset_price(self, broker_credentials: BrokerCredentials, symbol: str) -> Optional[Decimal]:
        """Récupérer le prix d'un actif depuis un courtier"""
        broker = self.get_broker_instance(broker_credentials)
        
        if not broker.authenticate():
            return None
        
        return broker.get_asset_price(symbol)

    def authenticate_saxo_with_code(self, broker_credentials: BrokerCredentials, authorization_code: str) -> bool:
        """Authentifier Saxo avec un code d'autorisation OAuth2"""
        if broker_credentials.broker_type != 'saxo':
            raise ValueError("Cette méthode est uniquement pour Saxo")
        
        broker = self.get_broker_instance(broker_credentials)
        return broker.authenticate_with_code(authorization_code)
    
    def get_saxo_auth_url(self, broker_credentials: BrokerCredentials, state: str = "xyz123") -> str:
        """Obtenir l'URL d'authentification Saxo"""
        if broker_credentials.broker_type != 'saxo':
            raise ValueError("Cette méthode est uniquement pour Saxo")
        
        broker = self.get_broker_instance(broker_credentials)
        return broker.get_auth_url(state)

    def sync_all_assets_from_saxo(self, broker_credentials: BrokerCredentials, limit: int = 1000) -> Dict[str, Any]:
        """Synchronise les actifs depuis Saxo Bank"""
        try:
            broker = self.get_broker_instance(broker_credentials)
            if not broker:
                return {'success': False, 'error': 'Broker non supporté'}
            
            # Récupérer les actifs depuis Saxo
            assets_data = broker.get_all_assets(limit=limit)
            
            if not assets_data:
                return {'success': False, 'error': 'Aucune donnée reçue de Saxo'}
            
            saved_count = 0
            updated_count = 0
            
            for asset_data in assets_data:
                try:
                    # Harmoniser les données Saxo
                    symbol = asset_data.get('Symbol', '')
                    name = asset_data.get('Description', '')
                    asset_type = asset_data.get('AssetType', 'Unknown')
                    
                    # Déterminer le marché
                    exchange_info = asset_data.get('Exchange', {})
                    market = exchange_info.get('ExchangeId', 'Unknown')
                    exchange_name = exchange_info.get('Name', '')
                    country_code = exchange_info.get('CountryCode', '')
                    
                    # Déterminer la devise
                    currency = asset_data.get('CurrencyCode', 'USD')
                    
                    # Vérifier si l'actif est tradable
                    is_tradable = asset_data.get('IsTradable', False)
                    
                    # Créer ou mettre à jour l'actif
                    all_asset, created = AllAssets.objects.update_or_create(
                        symbol=symbol,
                        platform='saxo',
                        defaults={
                            'name': name,
                            'asset_type': asset_type,
                            'market': market,
                            'currency': currency,
                            'exchange': exchange_name,
                            'is_tradable': is_tradable,
                            'saxo_uic': asset_data.get('Uic'),
                            'saxo_exchange_id': market,
                            'saxo_country_code': country_code,
                        }
                    )
                    
                    if created:
                        saved_count += 1
                    else:
                        updated_count += 1
                        
                except Exception as e:
                    print(f"❌ Erreur lors du traitement de l'actif Saxo {symbol}: {str(e)}")
                    continue
            
            return {
                'success': True,
                'saved_count': saved_count,
                'updated_count': updated_count,
                'total_processed': len(assets_data),
                'message': f"Synchronisation Saxo réussie: {saved_count} nouveaux, {updated_count} mis à jour"
            }
            
        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation Saxo: {str(e)}")
            return {'success': False, 'error': f"Erreur lors de la synchronisation: {str(e)}"}

    def sync_all_assets_from_binance(self, broker_credentials: BrokerCredentials) -> Dict[str, Any]:
        """Synchronise les actifs depuis Binance"""
        try:
            broker = self.get_broker_instance(broker_credentials)
            if not broker:
                return {'success': False, 'error': 'Broker non supporté'}
            
            # Récupérer les actifs depuis Binance
            assets_data = broker.get_all_assets()
            
            if not assets_data:
                return {'success': False, 'error': 'Aucune donnée reçue de Binance'}
            
            saved_count = 0
            updated_count = 0
            
            for asset_data in assets_data:
                try:
                    # Harmoniser les données Binance
                    symbol = asset_data.get('symbol', '')
                    base_asset = asset_data.get('baseAsset', '')
                    quote_asset = asset_data.get('quoteAsset', '')
                    status = asset_data.get('status', '')
                    
                    # Créer un nom descriptif
                    name = f"{base_asset}/{quote_asset}"
                    
                    # Déterminer le type d'actif (crypto par défaut)
                    asset_type = 'Crypto'
                    
                    # Déterminer le marché
                    market = 'SPOT'  # Par défaut, pourrait être FUTURES pour d'autres types
                    
                    # Vérifier si l'actif est tradable
                    is_tradable = status == 'TRADING'
                    
                    # Créer ou mettre à jour l'actif
                    all_asset, created = AllAssets.objects.update_or_create(
                        symbol=symbol,
                        platform='binance',
                        defaults={
                            'name': name,
                            'asset_type': asset_type,
                            'market': market,
                            'currency': quote_asset,
                            'exchange': 'Binance',
                            'is_tradable': is_tradable,
                            'binance_base_asset': base_asset,
                            'binance_quote_asset': quote_asset,
                            'binance_status': status,
                        }
                    )
                    
                    if created:
                        saved_count += 1
                    else:
                        updated_count += 1
                        
                except Exception as e:
                    print(f"❌ Erreur lors du traitement de l'actif Binance {symbol}: {str(e)}")
                    continue
            
            return {
                'success': True,
                'saved_count': saved_count,
                'updated_count': updated_count,
                'total_processed': len(assets_data),
                'message': f"Synchronisation Binance réussie: {saved_count} nouveaux, {updated_count} mis à jour"
            }
            
        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation Binance: {str(e)}")
            return {'success': False, 'error': f"Erreur lors de la synchronisation: {str(e)}"}

    def sync_all_assets_from_all_brokers(self) -> Dict[str, Any]:
        """Synchronise les actifs depuis tous les brokers configurés"""
        try:
            brokers = BrokerCredentials.objects.filter(is_active=True)
            total_results = []
            
            for broker in brokers:
                if broker.broker_type == 'saxo':
                    result = self.sync_all_assets_from_saxo(broker)
                elif broker.broker_type == 'binance':
                    result = self.sync_all_assets_from_binance(broker)
                else:
                    result = {'success': False, 'error': f'Broker {broker.broker_type} non supporté'}
                
                result['broker_name'] = broker.name
                result['broker_type'] = broker.broker_type
                total_results.append(result)
            
            # Calculer les totaux
            total_saved = sum(r.get('saved_count', 0) for r in total_results if r.get('success'))
            total_updated = sum(r.get('updated_count', 0) for r in total_results if r.get('success'))
            
            return {
                'success': True,
                'total_saved': total_saved,
                'total_updated': total_updated,
                'broker_results': total_results,
                'message': f"Synchronisation complète: {total_saved} nouveaux, {total_updated} mis à jour"
            }
            
        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation globale: {str(e)}")
            return {'success': False, 'error': f"Erreur lors de la synchronisation globale: {str(e)}"}


class SaxoAuthService:
    """Service spécifique pour l'authentification Saxo"""
    
    @staticmethod
    def get_auth_url(client_id: str, redirect_uri: str, state: str = "xyz123") -> str:
        """Générer l'URL d'autorisation Saxo"""
        from urllib.parse import urlencode
        
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid",
            "state": state
        }
        return f"https://sim.logonvalidation.net/authorize?{urlencode(params)}"
    
    @staticmethod
    def exchange_code_for_tokens(authorization_code: str, client_id: str, 
                                client_secret: str, redirect_uri: str) -> Dict[str, Any]:
        """Échanger le code d'autorisation contre des tokens"""
        import requests
        
        token_url = "https://sim.logonvalidation.net/token"
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        return response.json() 