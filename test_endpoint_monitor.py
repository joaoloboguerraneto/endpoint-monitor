import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock, call
import sys
import csv
import requests
from io import StringIO

# Importe o módulo a ser testado
from endpoint_monitor import EndpointMonitor


class TestEndpointMonitor(unittest.TestCase):
    """Testes para a classe EndpointMonitor"""

    def setUp(self):
        """Configurar ambiente de teste"""
        # Criar diretório temporário para configuração e dados
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Definir variáveis de ambiente específicas para cada teste
        config_dir = os.path.join(self.temp_dir.name, 'config')
        os.makedirs(config_dir, exist_ok=True)
        
        self.config_file = os.path.join(config_dir, 'config.json')
        self.data_store_file = os.path.join(config_dir, 'data-store.csv')
        
        # Salvar valores originais para restaurar no tearDown
        self.original_config_dir = os.environ.get('ENDPOINT_MONITOR_CONFIG_DIR')
        self.original_config_file = os.environ.get('ENDPOINT_MONITOR_CONFIG_FILE')
        self.original_data_store_file = os.environ.get('ENDPOINT_MONITOR_DATA_STORE_FILE')
        
        # Configurar valores para os testes
        os.environ['ENDPOINT_MONITOR_CONFIG_DIR'] = config_dir
        os.environ['ENDPOINT_MONITOR_CONFIG_FILE'] = self.config_file
        os.environ['ENDPOINT_MONITOR_DATA_STORE_FILE'] = self.data_store_file
    
    def tearDown(self):
        """Limpar após os testes"""
        # Restaurar variáveis de ambiente originais
        if self.original_config_dir:
            os.environ['ENDPOINT_MONITOR_CONFIG_DIR'] = self.original_config_dir
        else:
            os.environ.pop('ENDPOINT_MONITOR_CONFIG_DIR', None)
            
        if self.original_config_file:
            os.environ['ENDPOINT_MONITOR_CONFIG_FILE'] = self.original_config_file
        else:
            os.environ.pop('ENDPOINT_MONITOR_CONFIG_FILE', None)
            
        if self.original_data_store_file:
            os.environ['ENDPOINT_MONITOR_DATA_STORE_FILE'] = self.original_data_store_file
        else:
            os.environ.pop('ENDPOINT_MONITOR_DATA_STORE_FILE', None)
        
        # Remover diretório temporário
        self.temp_dir.cleanup()

    def test_load_config(self):
        """Testar carregamento da configuração"""
        # Definir configuração de exemplo
        sample_config = {
            "endpoints": {
                "test1": {
                    "url": "https://google.com",
                    "timeout": 5
                },
                "test2": {
                    "url": "https://mercedes-benz.io",
                    "timeout": 10
                }
            }
        }
        
        # Escrever configuração no arquivo
        with open(self.config_file, 'w') as f:
            json.dump(sample_config, f)
        
        # Instanciar monitor para carregar configuração
        monitor = EndpointMonitor()
        
        # Verificar se a configuração foi carregada corretamente
        self.assertEqual(monitor.config, sample_config)

    def test_add_endpoint(self):
        """Testar adição de um novo endpoint"""
        # Criar arquivo de configuração vazio
        with open(self.config_file, 'w') as f:
            json.dump({"endpoints": {}}, f)
        
        # Instanciar monitor
        monitor = EndpointMonitor()
        
        # Adicionar endpoint
        monitor.add_endpoint("test1", "https://google.com", 5)
        
        # Verificar se foi adicionado corretamente
        self.assertIn("test1", monitor.config["endpoints"])
        self.assertEqual(monitor.config["endpoints"]["test1"]["url"], "https://google.com")
        self.assertEqual(monitor.config["endpoints"]["test1"]["timeout"], 5)
        
        # Testar adição de endpoint duplicado
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = monitor.add_endpoint("test1", "https://example.com", 10)
            self.assertFalse(result)
            self.assertIn("already exists", fake_out.getvalue())

    @patch('requests.get')
    def test_check_endpoint_success(self, mock_get):
        """Testar verificação de endpoint que está online"""
        # Configurar mock de resposta
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Instanciar monitor
        monitor = EndpointMonitor()
        
        # Verificar endpoint
        result = monitor._check_endpoint("test1", {"url": "https://mercedes-benz.io", "timeout": 5})
        
        # Verificar resultado
        self.assertEqual(result["name"], "test1")
        self.assertEqual(result["url"], "https://mercedes-benz.io")
        self.assertEqual(result["status_code"], 200)
        self.assertTrue(result["is_available"])
        self.assertIsNotNone(result["timestamp"])
        self.assertIsNotNone(result["response_time"])

    @patch('requests.get')
    def test_check_endpoint_failure(self, mock_get):
        """Testar verificação de endpoint que está offline"""
        # Configurar mock para simular erro de conexão
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        # Instanciar monitor
        monitor = EndpointMonitor()
        
        # Verificar endpoint
        result = monitor._check_endpoint("test2", {"url": "https://mercedes-benz.io", "timeout": 10})
        
        # Verificar resultado
        self.assertEqual(result["name"], "test2")
        self.assertEqual(result["url"], "https://mercedes-benz.io")
        self.assertIsNone(result["status_code"])
        self.assertFalse(result["is_available"])
        self.assertIsNotNone(result["timestamp"])
        self.assertIsNone(result["response_time"])
        self.assertIn("Connection refused", result["error"])

    def test_fetch(self):
        """Testar método fetch para buscar status de endpoints"""
        # Configurar ambiente do teste
        sample_config = {
            "endpoints": {
                "test1": {
                    "url": "https://google.com",
                    "timeout": 5
                },
                "test2": {
                    "url": "https://mercedes-benz.io",
                    "timeout": 10
                }
            }
        }
        
        # Escrever configuração no arquivo
        with open(self.config_file, 'w') as f:
            json.dump(sample_config, f)
        
        # Criar mocks para os métodos internos
        with patch('endpoint_monitor.EndpointMonitor._check_endpoint') as mock_check, \
             patch('endpoint_monitor.EndpointMonitor._save_result') as mock_save:
            
            # Configurar retornos do mock
            mock_check.side_effect = [
                {
                    "name": "test1",
                    "url": "https://google.com",
                    "timestamp": "2023-01-01T12:00:00",
                    "status_code": 200,
                    "response_time": 150.5,
                    "is_available": True
                },
                {
                    "name": "test2",
                    "url": "https://mercedes-benz.io",
                    "timestamp": "2023-01-01T12:00:00",
                    "status_code": 404,
                    "response_time": 200.3,
                    "is_available": False
                }
            ]
            
            # Instanciar monitor
            monitor = EndpointMonitor()
            
            # Executar método fetch
            results = monitor.fetch(output=False)
            
            # Verificar se o método _check_endpoint foi chamado duas vezes (uma para cada endpoint)
            self.assertEqual(mock_check.call_count, 2)
            
            # Verificar se os resultados foram salvos
            self.assertEqual(mock_save.call_count, 2)
            
            # Verificar se o método retornou dois resultados
            self.assertEqual(len(results), 2)
            
            # Reiniciar os mocks para o próximo teste
            mock_check.reset_mock()
            mock_save.reset_mock()
            
            # Configurar mock para testar busca de endpoint específico
            mock_check.return_value = {
                "name": "test1",
                "url": "https://google.com",
                "timestamp": "2023-01-01T12:00:00",
                "status_code": 200,
                "response_time": 150.5,
                "is_available": True
            }
            
            # Testar busca de endpoint específico
            results = monitor.fetch(endpoint_names=["test1"], output=False)
            
            # Verificar se _check_endpoint foi chamado apenas uma vez
            self.assertEqual(mock_check.call_count, 1)
            
            # Verificar se recebemos apenas um resultado
            self.assertEqual(len(results), 1)
            
            # Verificar se o método foi chamado com o nome correto
            mock_check.assert_called_with("test1", {"url": "https://google.com", "timeout": 5})


if __name__ == '__main__':
    unittest.main()