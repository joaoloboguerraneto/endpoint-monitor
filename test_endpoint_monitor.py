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
from endpoint_monitor import EndpointMonitor, CONFIG_FILE, DATA_STORE_FILE


class TestEndpointMonitor(unittest.TestCase):
    """Testes para a classe EndpointMonitor"""

    def setUp(self):
        """Configurar ambiente de teste"""
        # Criar diretório temporário para configuração e dados
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Definir caminhos para os arquivos de teste
        config_dir = os.path.join(self.temp_dir.name, 'config')
        os.makedirs(config_dir, exist_ok=True)
        
        self.test_config_file = os.path.join(config_dir, 'config.json')
        self.test_data_store_file = os.path.join(config_dir, 'data-store.csv')
        
        # Salvar caminhos originais para restaurar depois
        self.original_config_file = CONFIG_FILE
        self.original_data_store_file = DATA_STORE_FILE
        
        # Patch as constantes no módulo endpoint_monitor
        self.config_file_patcher = patch('endpoint_monitor.CONFIG_FILE', self.test_config_file)
        self.data_store_file_patcher = patch('endpoint_monitor.DATA_STORE_FILE', self.test_data_store_file)
        
        self.mock_config_file = self.config_file_patcher.start()
        self.mock_data_store_file = self.data_store_file_patcher.start()
    
    def tearDown(self):
        """Limpar após os testes"""
        # Parar os patchers
        self.config_file_patcher.stop()
        self.data_store_file_patcher.stop()
        
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
                }
            }
        }
        
        # Escrever configuração no arquivo
        with open(self.test_config_file, 'w') as f:
            json.dump(sample_config, f)
        
        # Instanciar monitor para carregar configuração
        monitor = EndpointMonitor()
        
        # Verificar se a configuração foi carregada corretamente
        self.assertEqual(monitor.config, sample_config)

    def test_add_endpoint(self):
        """Testar adição de um novo endpoint"""
        # Criar arquivo de configuração vazio
        with open(self.test_config_file, 'w') as f:
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

    @patch('endpoint_monitor.ThreadPoolExecutor')
    def test_fetch(self, mock_executor):
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
        with open(self.test_config_file, 'w') as f:
            json.dump(sample_config, f)
            
        # Configurar mocks para o ThreadPoolExecutor
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        
        # Configurar resultados dos mocks
        result1 = {
            "name": "test1",
            "url": "https://google.com",
            "timestamp": "2023-01-01T12:00:00",
            "status_code": 200,
            "response_time": 150.5,
            "is_available": True
        }
        
        result2 = {
            "name": "test2",
            "url": "https://mercedes-benz.io",
            "timestamp": "2023-01-01T12:00:00",
            "status_code": 404,
            "response_time": 200.3,
            "is_available": False
        }
        
        # Configurar o Future para o primeiro endpoint
        future1 = MagicMock()
        future1.result.return_value = result1
        
        # Configurar o Future para o segundo endpoint
        future2 = MagicMock()
        future2.result.return_value = result2
        
        # Fazer o mock_executor_instance.submit retornar os futures adequados
        mock_executor_instance.submit.side_effect = [future1, future2]
        
        # Patch o método _save_result para evitar escrita em disco
        with patch.object(EndpointMonitor, '_save_result') as mock_save:
            # Instanciar monitor
            monitor = EndpointMonitor()
            
            # Executar método fetch
            results = monitor.fetch(output=False)
            
            # Verificar se submit foi chamado duas vezes (uma para cada endpoint)
            self.assertEqual(mock_executor_instance.submit.call_count, 2)
            
            # Verificar se _save_result foi chamado duas vezes
            self.assertEqual(mock_save.call_count, 2)
            
            # Verificar se retornou dois resultados
            self.assertEqual(len(results), 2)
            
            # Verificar conteúdo dos resultados
            self.assertIn(result1, results)
            self.assertIn(result2, results)
            
        # Testar fetch com endpoints específicos
        with patch.object(EndpointMonitor, '_save_result'), \
             patch.object(EndpointMonitor, '_check_endpoint') as mock_check:
            
            mock_check.return_value = result1
            
            # Redefinir mock para teste de endpoints específicos
            mock_executor_instance.reset_mock()
            mock_executor_instance.submit.side_effect = [future1]
            
            # Chamar fetch com nome de endpoint específico
            results = monitor.fetch(endpoint_names=["test1"], output=False)
            
            # Verificar se submit foi chamado apenas uma vez
            self.assertEqual(mock_executor_instance.submit.call_count, 1)
            
            # Verificar o resultado
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0], result1)


if __name__ == '__main__':
    unittest.main()