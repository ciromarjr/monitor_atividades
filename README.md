# 📊 Sistema de Monitoramento de Atividades em Equipe

Um sistema web robusto desenvolvido com Streamlit para monitoramento em tempo real de atividades de equipe, oferecendo diferentes níveis de acesso e visualizações personalizadas para cada tipo de usuário.

![Licença](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-v1.20+-red.svg)
![Versão](https://img.shields.io/badge/version-1.0.0-green.svg)

## 🌟 Funcionalidades

### 👥 Níveis de Acesso
- **Administrador**: Gerenciamento completo do sistema
- **Supervisor**: Monitoramento e análise de atividades
- **Usuário**: Registro e acompanhamento de atividades próprias

### 📱 Interface Principal
- Dashboard interativo e responsivo
- Métricas em tempo real
- Gráficos e visualizações dinâmicas
- Sistema de notificações

### 📊 Recursos de Análise
- Timeline de atividades
- Métricas de produtividade
- Distribuição de status
- Performance por departamento
- Análise de workload

## 🚀 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/sistema-monitoramento.git
cd sistema-monitoramento
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute a aplicação:
```bash
streamlit run app.py
```

## 📋 Requisitos

Crie um arquivo `requirements.txt` com as seguintes dependências:

```
streamlit>=1.20.0
pandas>=1.5.0
plotly>=5.10.0
pillow>=9.0.0
sqlite3
```

## 🔧 Configuração

1. Configure o banco de dados:
   - O sistema utiliza SQLite por padrão
   - O banco será criado automaticamente na primeira execução
   - Localização padrão: `./team_activities.db`

2. Usuário administrativo padrão:
   - Username: `admin`
   - Senha: `admin`
   - *Recomendamos alterar a senha no primeiro acesso*

## 📱 Interface e Funcionalidades

### Interface Administrativa
- Cadastro e gerenciamento de usuários
- Visualização completa do dashboard
- Configurações do sistema
- Geração de relatórios

### Interface do Supervisor
- Monitoramento em tempo real
- Análise de performance
- Relatórios de equipe
- Gestão de workload

### Interface do Usuário
- Registro de atividades
- Acompanhamento de status
- Dashboard pessoal
- Histórico de atividades

## 🔒 Segurança

- Senhas criptografadas com SHA-256
- Controle de sessão
- Validação de inputs
- Proteção contra SQL injection
- Logs de atividades

## 📈 Personalização

### Temas e Cores
```python
# Exemplo de personalização de cores
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton button {
        background-color: #4CAF50;
    }
    </style>
""", unsafe_allow_html=True)
```

### Métricas Personalizadas
```python
# Adicionar nova métrica
def custom_metric():
    # Sua lógica aqui
    return value
```

## 🤝 Contribuição

1. Faça um Fork do projeto
2. Crie uma Branch para sua Feature (`git checkout -b feature/AmazingFeature`)
3. Faça o Commit de suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Faça o Push para a Branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 📫 Contato

Seu Nome - [@seutwitter](https://twitter.com/seutwitter) - email@exemplo.com

Link do Projeto: [https://github.com/seu-usuario/sistema-monitoramento](https://github.com/seu-usuario/sistema-monitoramento)

## 🙏 Agradecimentos

- [Streamlit](https://streamlit.io/)
- [Plotly](https://plotly.com/)
- [Python](https://www.python.org/)
- [SQLite](https://www.sqlite.org/)

---
⭐️ From [seu-usuario](https://github.com/seu-usuario)
