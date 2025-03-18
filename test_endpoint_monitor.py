import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
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
        
        # Sobrescrever CONFIG_DIR, CONFIG_FILE, e DATA_STORE_FILE
        self.original_config_dir = os.environ.get('ENDPOINT_MONITOR_CONFIG_DIR')
        self.original_config_file = os.environ.get('ENDPOINT_MONITOR_CONFIG_FILE')
        self.original_data_store_file = os.environ.get('ENDPOINT_MONITOR_DATA_STORE_FILE')
        
        os.environ['ENDPOINT_MONITOR_CONFIG_DIR'] = self.temp_dir.name
        os.environ['ENDPOINT_MONITOR_CONFIG_FILE'] = os.path.join(self.temp_dir.name, 'config.json')
        os.environ['ENDPOINT_MONITOR_DATA_STORE_FILE'] = os.path.join(self.temp_dir.name, 'data-store.csv')
        
        # Criar configuração de exemplo
        self.sample_config = {
            "endpoints": {
                "test1": {
                    "url": "https://example.com",
                    "timeout": 5
                },
                "test2": {
                    "url": "https://example.org",
                    "timeout": 10
                }
            }
        }
        
        with open(os.environ['ENDPOINT_MONITOR_CONFIG_FILE'], 'w') as f:
            json.dump(self.sample_config, f)

    def tearDown(self):
        """Limpar após os testes"""
        self.temp_dir.cleanup()
        
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

    def test_load_config(self):
        """Testar carregamento da configuração"""
        monitor = EndpointMonitor()
        self.assertEqual(monitor.config, self.sample_config)

    def test_add_endpoint(self):
        """Testar adição de novo endpoint"""
        monitor = EndpointMonitor()
        
        # Adicionar novo endpoint
        monitor.add_endpoint("test3", "https://example.net", 15)
        
        # Verificar se foi adicionado
        self.assertIn("test3", monitor.config["endpoints"])
        self.assertEqual(monitor.config["endpoints"]["test3"]["url"], "https://example.net")
        self.assertEqual(monitor.config["endpoints"]["test3"]["timeout"], 15)
        
        # Testar adição de duplicata
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = monitor.add_endpoint("test3", "https://example.net", 15)
            self.assertFalse(result)
            self.assertIn("already exists", fake_out.getvalue())

    @patch('requests.get')
    def test_check_endpoint_success(self, mock_get):
        """Testar verificação de endpoint que está online"""
        # Simular a resposta
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        monitor = EndpointMonitor()
        result = monitor._check_endpoint("test1", {"url": "https://example.com", "timeout": 5})
        
        # Verificar o resultado
        self.assertEqual(result["name"], "test1")
        self.assertEqual(result["url"], "https://example.com")
        self.assertEqual(result["status_code"], 200)
        self.assertTrue(result["is_available"])
        self.assertIsNotNone(result["timestamp"])
        self.assertIsNotNone(result["response_time"])

    @patch('requests.get')
    def test_check_endpoint_failure(self, mock_get):
        """Testar verificação de endpoint que está offline"""
        # Simular um erro de conexão
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        monitor = EndpointMonitor()
        result = monitor._check_endpoint("test1", {"url": "https://example.com", "timeout": 5})
        
        # Verificar o resultado
        self.assertEqual(result["name"], "test1")
        self.assertEqual(result["url"], "https://example.com")
        self.assertIsNone(result["status_code"])
        self.assertFalse(result["is_available"])
        self.assertIsNotNone(result["timestamp"])
        self.assertIsNone(result["response_time"])
        self.assertIn("Connection refused", result["error"])

    @patch('endpoint_monitor.EndpointMonitor._check_endpoint')
    def test_fetch(self, mock_check):
        """Testar busca de endpoints"""
        # Simular o método _check_endpoint
        mock_check.side_effect = [
            {
                "name": "test1",
                "url": "https://example.com",
                "timestamp": "2023-01-01T12:00:00",
                "status_code": 200,
                "response_time": 150.5,
                "is_available": True
            },
            {
                "name": "test2",
                "url": "https://example.org",
                "timestamp": "2023-01-01T12:00:00",
                "status_code": None,
                "response_time": None,
                "is_available": False,
                "error": "Connection refused"
            }
        ]
        
        monitor = EndpointMonitor()
        
        # Testar busca de todos os endpoints
        results = monitor.fetch(output=False)
        self.assertEqual(len(results), 2)
        
        # Testar busca de endpoints específicos
        results = monitor.fetch(endpoint_names=["test1"], output=False)
        mock_check.assert_called_with("test1", {"url": "https://example.com", "timeout": 5})


if __name__ == '__main__':
    unittest.main()