import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time

# Configuração da página
st.set_page_config(layout='wide')

# Função para formatar números
def formata_numero(valor, prefixo=''):
    for unidade in ['', 'mil']:
        if valor < 1000:
            return f'{prefixo} {valor:.2f} {unidade}'
        valor /= 1000
    return f'{prefixo} {valor:.2f} milhões'

# Função para converter DataFrame em CSV
@st.cache_data
def converte_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Função para exibir mensagem de sucesso
def mensagem_sucesso():
    sucesso = st.success('Arquivo baixado com sucesso!', icon="✅")
    time.sleep(5)
    sucesso.empty()

# Página 1: Dados Brutos
def pagina_dados_brutos():
    st.title('DADOS BRUTOS')

    url = 'https://labdados.com/produtos'
    response = requests.get(url)
    dados = pd.DataFrame.from_dict(response.json())
    dados['Data da Compra'] = pd.to_datetime(dados['Data da Compra'], format='%d/%m/%Y')

    with st.expander('Colunas'):
        colunas = st.multiselect('Selecione as colunas', list(dados.columns), list(dados.columns))

    st.sidebar.title('Filtros')
    with st.sidebar.expander('Nome do produto'):
        produtos = st.multiselect('Selecione os produtos', dados['Produto'].unique(), dados['Produto'].unique())
    with st.sidebar.expander('Categoria do produto'):
        categoria = st.multiselect('Selecione as categorias', dados['Categoria do Produto'].unique(), dados['Categoria do Produto'].unique())
    with st.sidebar.expander('Preço do produto'):
        preco = st.slider('Selecione o preço', 0, 5000, (0, 5000))
    with st.sidebar.expander('Frete da venda'):
        frete = st.slider('Frete', 0, 250, (0, 250))
    with st.sidebar.expander('Data da compra'):
        data_compra = st.date_input('Selecione a data', (dados['Data da Compra'].min(), dados['Data da Compra'].max()))
    with st.sidebar.expander('Vendedor'):
        vendedores = st.multiselect('Selecione os vendedores', dados['Vendedor'].unique(), dados['Vendedor'].unique())
    with st.sidebar.expander('Local da compra'):
        local_compra = st.multiselect('Selecione o local da compra', dados['Local da compra'].unique(), dados['Local da compra'].unique())
    with st.sidebar.expander('Avaliação da compra'):
        avaliacao = st.slider('Selecione a avaliação da compra', 1, 5, value=(1, 5))
    with st.sidebar.expander('Tipo de pagamento'):
        tipo_pagamento = st.multiselect('Selecione o tipo de pagamento', dados['Tipo de pagamento'].unique(), dados['Tipo de pagamento'].unique())
    with st.sidebar.expander('Quantidade de parcelas'):
        qtd_parcelas = st.slider('Selecione a quantidade de parcelas', 1, 24, (1, 24))

    query = '''
    Produto in @produtos and \
    `Categoria do Produto` in @categoria and \
    @preco[0] <= Preço <= @preco[1] and \
    @frete[0] <= Frete <= @frete[1] and \
    @data_compra[0] <= `Data da Compra` <= @data_compra[1] and \
    Vendedor in @vendedores and \
    `Local da compra` in @local_compra and \
    @avaliacao[0] <= `Avaliação da compra` <= @avaliacao[1] and \
    `Tipo de pagamento` in @tipo_pagamento and \
    @qtd_parcelas[0] <= `Quantidade de parcelas` <= @qtd_parcelas[1]
    '''

    dados_filtrados = dados.query(query)
    dados_filtrados = dados_filtrados[colunas]

    st.dataframe(dados_filtrados)

    st.markdown(f'A tabela possui :blue[{dados_filtrados.shape[0]}] linhas e :blue[{dados_filtrados.shape[1]}] colunas')

    st.markdown('Escreva um nome para o arquivo')
    coluna1, coluna2 = st.columns(2)
    with coluna1:
        nome_arquivo = st.text_input('', label_visibility='collapsed', value='dados')
        nome_arquivo += '.csv'
    with coluna2:
        st.download_button(
            'Fazer o download da tabela em csv',
            data=converte_csv(dados_filtrados),
            file_name=nome_arquivo,
            mime='text/csv',
            on_click=mensagem_sucesso
        )

# Página 2: Dashboard
def pagina_dashboard():
    st.title('DASHBOARD DE VENDAS :shopping_trolley:')

    url = 'https://labdados.com/produtos'
    regioes = ['Brasil', 'Centro-Oeste', 'Nordeste', 'Norte', 'Sudeste', 'Sul']

    st.sidebar.title('Filtros')
    regiao = st.sidebar.selectbox('Região', regioes)

    if regiao == 'Brasil':
        regiao = ''

    todos_anos = st.sidebar.checkbox('Dados de todo o período', value=True)
    if todos_anos:
        ano = ''
    else:
        ano = st.sidebar.slider('Ano', 2020, 2023)

    query_string = {'regiao': regiao.lower(), 'ano': ano}
    response = requests.get(url, params=query_string)
    dados = pd.DataFrame.from_dict(response.json())
    dados['Data da Compra'] = pd.to_datetime(dados['Data da Compra'], format='%d/%m/%Y')

    filtro_vendedores = st.sidebar.multiselect('Vendedores', dados['Vendedor'].unique())
    if filtro_vendedores:
        dados = dados[dados['Vendedor'].isin(filtro_vendedores)]

    # Tabelas e gráficos
    receita_estados = dados.groupby('Local da compra')[['Preço']].sum()
    receita_estados = dados.drop_duplicates(subset='Local da compra')[['Local da compra', 'lat', 'lon']].merge(receita_estados, left_on='Local da compra', right_index=True).sort_values('Preço', ascending=False)

    receita_mensal = dados.set_index('Data da Compra').groupby(pd.Grouper(freq='M'))['Preço'].sum().reset_index()
    receita_mensal['Ano'] = receita_mensal['Data da Compra'].dt.year
    receita_mensal['Mes'] = receita_mensal['Data da Compra'].dt.month_name()

    receita_categorias = dados.groupby('Categoria do Produto')[['Preço']].sum().sort_values('Preço', ascending=False)

    vendas_estados = pd.DataFrame(dados.groupby('Local da compra')['Preço'].count())
    vendas_estados = dados.drop_duplicates(subset='Local da compra')[['Local da compra', 'lat', 'lon']].merge(vendas_estados, left_on='Local da compra', right_index=True).sort_values('Preço', ascending=False)

    vendas_mensal = pd.DataFrame(dados.set_index('Data da Compra').groupby(pd.Grouper(freq='M'))['Preço'].count()).reset_index()
    vendas_mensal['Ano'] = vendas_mensal['Data da Compra'].dt.year
    vendas_mensal['Mes'] = vendas_mensal['Data da Compra'].dt.month_name()

    vendas_categorias = pd.DataFrame(dados.groupby('Categoria do Produto')['Preço'].count().sort_values(ascending=False))

    vendedores = pd.DataFrame(dados.groupby('Vendedor')['Preço'].agg(['sum', 'count']))

    # Gráficos
    fig_mapa_receita = px.scatter_geo(receita_estados,
                                      lat='lat',
                                      lon='lon',
                                      scope='south america',
                                      size='Preço',
                                      template='seaborn',
                                      hover_name='Local da compra',
                                      hover_data={'lat': False, 'lon': False},
                                      title='Receita por estado')

    fig_receita_mensal = px.line(receita_mensal,
                                 x='Mes',
                                 y='Preço',
                                 markers=True,
                                 range_y=(0, receita_mensal.max()),
                                 color='Ano',
                                 line_dash='Ano',
                                 title='Receita mensal')

    fig_receita_mensal.update_layout(yaxis_title='Receita')

    fig_receita_estados = px.bar(receita_estados.head(),
                                 x='Local da compra',
                                 y='Preço',
                                 text_auto=True,
                                 title='Top estados (receita)')

    fig_receita_estados.update_layout(yaxis_title='Receita')

    fig_receita_categorias = px.bar(receita_categorias,
                                    text_auto=True,
                                    title='Receita por categoria')

    fig_receita_categorias.update_layout(yaxis_title='Receita')

    fig_mapa_vendas = px.scatter_geo(vendas_estados,
                                     lat='lat',
                                     lon='lon',
                                     scope='south america',
                                     template='seaborn',
                                     size='Preço',
                                     hover_name='Local da compra',
                                     hover_data={'lat': False, 'lon': False},
                                     title='Vendas por estado')

    fig_vendas_estados = px.bar(vendas_estados.head(),
                                x='Local da compra',
                                y='Preço',
                                text_auto=True,
                                title='Top 5 estados')

    fig_vendas_estados.update_layout(yaxis_title='Quantidade de vendas')

    fig_vendas_mensal = px.line(vendas_mensal,
                                x='Mes',
                                y='Preço',
                                markers=True,
                                range_y=(0, vendas_mensal.max()),
                                color='Ano',
                                line_dash='Ano',
                                title='Quantidade de vendas mensal')

    fig_vendas_mensal.update_layout(yaxis_title='Quantidade de vendas')

    fig_vendas_categorias = px.bar(vendas_categorias,
                                   text_auto=True,
                                   title='Vendas por categoria')

    fig_vendas_categorias.update_layout(showlegend=False, yaxis_title='Quantidade de vendas')

    # Visualização no Streamlit
    aba1, aba2, aba3 = st.tabs(['Receita', 'Quantidade de vendas', 'Vendedores'])

    with aba1:
        coluna1, coluna2 = st.columns(2)
        with coluna1:
            st.metric('Receita', formata_numero(dados['Preço'].sum(), 'R$'))
            st.plotly_chart(fig_mapa_receita, use_container_width=True)
            st.plotly_chart(fig_receita_estados, use_container_width=True)
        with coluna2:
            st.metric('Quantidade de vendas', formata_numero(dados.shape[0]))
            st.plotly_chart(fig_receita_mensal, use_container_width=True)
            st.plotly_chart(fig_receita_categorias, use_container_width=True)

    with aba2:
        coluna1, coluna2 = st.columns(2)
        with coluna1:
            st.metric('Receita', formata_numero(dados['Preço'].sum(), 'R$'))
            st.plotly_chart(fig_mapa_vendas, use_container_width=True)
            st.plotly_chart(fig_vendas_estados, use_container_width=True)
        with coluna2:
            st.metric('Quantidade de vendas', formata_numero(dados.shape[0]))
            st.plotly_chart(fig_vendas_mensal, use_container_width=True)
            st.plotly_chart(fig_vendas_categorias, use_container_width=True)

    with aba3:
        qtd_vendedores = st.number_input('Quantidade de vendedores', 2, 10, 5)
        coluna1, coluna2 = st.columns(2)
        with coluna1:
            st.metric('Receita', formata_numero(dados['Preço'].sum(), 'R$'))
            fig_receita_vendedores = px.bar(vendedores[['sum']].sort_values('sum', ascending=False).head(qtd_vendedores),
                                            x='sum',
                                            y=vendedores[['sum']].sort_values('sum', ascending=False).head(qtd_vendedores).index,
                                            text_auto=True,
                                            title=f'Top {qtd_vendedores} vendedores (receita)')
            st.plotly_chart(fig_receita_vendedores, use_container_width=True)
        with coluna2:
            st.metric('Quantidade de vendas', formata_numero(dados.shape[0]))
            fig_vendas_vendedores = px.bar(vendedores[['count']].sort_values('count', ascending=False).head(qtd_vendedores),
                                           x='count',
                                           y=vendedores[['count']].sort_values('count', ascending=False).head(qtd_vendedores).index,
                                           text_auto=True,
                                           title=f'Top {qtd_vendedores} vendedores (quantidade de vendas)')
            st.plotly_chart(fig_vendas_vendedores, use_container_width=True)

# Menu de navegação
pagina = st.sidebar.selectbox('Selecione a página', ['Dados Brutos', 'Dashboard'])

if pagina == 'Dados Brutos':
    pagina_dados_brutos()
else:
    pagina_dashboard()