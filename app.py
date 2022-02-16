from decimal import ROUND_DOWN
from os import stat
import requests
import json
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import time
from trend_capturer import TrendCapturer

plt.style.use('dark_background')


def run_query(uri, query, status_code):
    request = requests.post(uri, json={'query': query})
    if request.status_code == status_code:
        return request.json()
    else:
        raise Exception(f"Unexpected status code returned: {request.status_code}")

zeitgeist_uri = 'https://processor.zeitgeist.pm/graphql'
status_code = 200

total_markets_query = '''
        query MyQuery {
            marketsConnection {
                totalCount
            }
        }
    '''
total_markets = run_query(zeitgeist_uri, total_markets_query, status_code)
total_markets_number = str(total_markets['data']['marketsConnection']['totalCount'])



section = st.sidebar.selectbox(
    "Section to Evaluate",
    ("Accounts", "Markets", "Transfers", "User Value")
)

if section == 'Accounts':

    with st.spinner('Wait for it...'):
        time.sleep(3)

    title_container = st.container()
    col1, col2 = st.columns([4, 20])
    with title_container:
        with col1:
            st.image('./moon_white.png', width= 100)
        with col2:
            st.markdown('<h1>Zeitgeist Analytics</h1> </br>',
                        unsafe_allow_html=True)

    solved_markets_query= '''
                query MyQuery {
                markets(where: {status_eq: "Resolved"}) {
                        outcomeAssets
                        report {
                            outcome {
                                categorical
                                scalar
                            }
                        }
                    }
                }
            '''

    solved_markets = run_query(zeitgeist_uri, solved_markets_query, status_code)
    solved_markets_data = solved_markets['data']['markets']

    winning_outcomes = {}

    for i in solved_markets_data:
        asset_winner = str(i['report']['outcome']['categorical'])
        ending_string = f',{asset_winner}]'
        temp = i['outcomeAssets'][0].split(',')[0]
        x = temp + ending_string

        market_id = temp.split('[')[-1]
        
        winning_outcomes[market_id] = x

    st.write('ASSET DICTIONARY')
    st.write(winning_outcomes)



    user_id = st.sidebar.text_input('Account ID')
    if user_id:
        try:
            query = '''
            query MyQuery {
            assetBalances(where: {account: {id_eq: "'''+ user_id + '''"}}) {
                accountId
                balance
                id
                account {
                assetBalances {
                    balance
                    assetId
                }
                }
            }
            }
            '''


            result = run_query(zeitgeist_uri, query, status_code)
            result = result['data']['assetBalances']

            balances = {}

            for r in result:
                account_id = r['accountId']
                assets = r['account']['assetBalances']
                asset_dict = {}
                for asset in assets:
                    value = int(asset['balance'])/10000000000
                    if asset['assetId'] == 'Ztg':
                        asset_dict[asset['assetId'].upper()] = value
                    elif asset['assetId'][:3] == '{\"c':
                        asset_value = asset['assetId'].split(':')[-1][:-1]
                        asset_id_new = 'Cat '+asset_value
                        asset_dict[asset_id_new] = value
                    else:
                        asset_value = asset['assetId'].split(':')[-1][:-1]
                        asset_id_new = 'Pool '+asset_value
                        asset_dict[asset_id_new] = value
                    

                balances[account_id] = asset_dict

            st.write(f'''
            ### User profile - {user_id}
            ''')
            st.write(f"ZTG Balance: \t {balances[user_id]['ZTG']} ZTG")
            st.write(f'Number of assets bought: \t {int(len(balances[user_id]))-1}')


            market_assets = []
            pool_share = []
            for i in list(balances[user_id].keys()):
                if (i != 'ZTG') & (i[:4] != 'Pool'):
                    market_id = i.split(',')[0][-1]
                    market_assets += [market_id]
                elif i != 'ZTG':
                    pool_share += [i]
                    
                    
            try:
                st.write(f'Traded in {len(set(market_assets))} markets')
                st.write(f'Provided Liquidity in {len(set(pool_share))} markets')
            except:
                pass

            
            chart_data = pd.DataFrame.from_dict(balances[user_id], orient="index")

            fig, ax = plt.subplots()
            ax.barh(chart_data.index, chart_data[chart_data.columns[0]])
            # ax.set_yticks(y_pos, labels=people)
            ax.invert_yaxis()  # labels read top-to-bottom
            ax.set_ylabel('Assets')
            ax.set_xlabel('Amount')

            # st.bar_chart(chart_data)
            st.pyplot(fig)

            st.write('Market Creation')
            market_creation_query= '''
                query MyQuery {
                    markets(where: {createdById_eq: "'''+user_id+'''"}) {
                        id
                        tags
                    }
                }

            '''
            markets_by_user = run_query(zeitgeist_uri, market_creation_query, status_code)
            number_of_markets = len(markets_by_user['data']['markets'])
            st.write(f'This user created {number_of_markets} markets')
            if number_of_markets > 0:
                pass

            st.markdown('## User Value')
            
            if len(set(market_assets)) >0:
                value_query = '''
                query MyQuery {
                    historicalAssetBalances(where: {account: {id_eq: "'''+ user_id + '''"}}) {
                        assetId
                        amount
                        blockNumber
                        balance
                        event
                        createdAt
                    }
                }
                '''

                user_txs = run_query(zeitgeist_uri, value_query, status_code)

                user_txs_data = user_txs['data']['historicalAssetBalances']
                total_txs = len(user_txs_data)
                st.write(f'Total operations: {total_txs}')

                total_vol = 0
                balance = 0

                market_invested = {}
                tags_volume = {}
                
                for i in user_txs_data:
                    if i['assetId'] == 'Ztg':
                        value = int(i['amount'])/10000000000
                        total_vol += abs(value)
                        balance += value

                    elif (i['assetId'] != 'Ztg') & ('pool' not in i['assetId']):
                        market_id = i['assetId'].split(',')[0].split('[')[-1]
                        if market_id in market_invested.keys():
                            market_invested[market_id] += 1
                        else:
                            market_invested[market_id] = 1

                        market_tag_query = '''
                        query MyQuery {
                            markets(where: {marketId_eq: '''+market_id+'''}) {
                                tags
                            }
                        }
                        '''
                        market_tags = run_query(zeitgeist_uri, market_tag_query, status_code)
                        market_tag_data = market_tags['data']['markets'][0]['tags']
                        for tag in market_tag_data:
                            if tag in tags_volume.keys():
                                tags_volume[tag] += abs(int(i['amount'])/10000000000)
                            else:
                                tags_volume[tag] = abs(int(i['amount'])/10000000000)

                st.write(f'Total volume traded: {round(total_vol,2)} ZTG')
                # st.write(f'Balance: {round(balance,2)} ZTG')
                # st.write(f'The user participated in {len(market_invested.keys())} markets')
                st.markdown(''' ## Total volume traded by Tag
                    Note: keep in mind that a market can be label under several tags
                    ''')

                if len(tags_volume.keys()) > 0:
                    st.write(tags_volume)

                last_activity = user_txs_data[-1]['createdAt']

                st.write(f'Last Activity: {last_activity}')
            
            else:
                st.markdown('''## The user haven't any value yet
                    This is because he/she haven't traded in any market yet
                
                ''')

        except:
            st.error('An invalid account ID was provided. Please double check it')
    else:
        st.info('Please, specify an Account ID')

if section == 'Markets':
    
    with st.spinner('Wait for it...'):
        time.sleep(3)

    title_container = st.container()
    col1, col2 = st.columns([4, 20])
    with title_container:
        with col1:
            st.image('./moon_white.png', width= 100)
        with col2:
            st.markdown('<h1>Zeitgeist Analytics</h1> </br>',
                        unsafe_allow_html=True)

    
    st.write(f'Total number of markets: {total_markets_number}')

    market_query = '''
        query MyQuery {
            markets (limit: '''+total_markets_number+'''){
                id
                tags
            }
        }
    '''
    markets = run_query(zeitgeist_uri, market_query, status_code)

    tags_count = {}
    for i in range(int(total_markets_number)):
        tags = markets['data']['markets'][i]['tags']
        if tags:
            for tag in tags:
                if tag in tags_count.keys():
                    tags_count[tag] += 1
                else:
                    tags_count[tag] = 1
        else:
            if 'None' in tags_count.keys():
                tags_count['None'] += 1
            else:
                tags_count['None'] = 1

    df = pd.DataFrame.from_dict(tags_count, orient = 'index', columns = ['Count'])
    st.bar_chart(df, use_container_width=True)
        
    tag_count_list = []
    for key, value in tags_count.items():
        item = f'{key} ({value})'
        tag_count_list += [item]
    # market_tag_labels = st.multiselect('Market Tags', list(tags_count.keys()))
    tag_list = sorted(tag_count_list)
    market_tag_labels = st.selectbox('Market Tags', tag_list)

    if market_tag_labels:
        category = market_tag_labels.split(' ')[0]
        st.write('Correlated categories')
        if category == 'None':
            market_subquery_tags = '''
                query MyQuery {
                    markets (limit: '''+total_markets_number+''', where: {tags_containsNone: ""}){
                        id
                        tags
                        question
                        slug
                        status
                    }
                }
            '''
        else:    
            market_subquery_tags = '''
                query MyQuery {
                    markets (limit: '''+total_markets_number+''', where: {tags_containsAll: "'''+category+'''"}){
                        id
                        tags
                        question
                        slug
                        status
                    }
                }
            '''
        subquery_tags = run_query(zeitgeist_uri, market_subquery_tags, status_code)


        subquery_data = subquery_tags['data']['markets']
        subquery_tags_count = {}
        for i in range(len(subquery_data)):
            tags = subquery_data[i]['tags']
            if tags:
                for tag in tags:
                    if tag != category:
                        if tag in subquery_tags_count.keys():
                            subquery_tags_count[tag] += 1
                        else:
                            subquery_tags_count[tag] = 1
            else:
                if 'None' in subquery_tags_count.keys():
                    subquery_tags_count['None'] += 1
                else:
                    subquery_tags_count['None'] = 1

        subquery_df = pd.DataFrame.from_dict(subquery_tags_count, orient = 'index', columns = ['Count'])
        st.bar_chart(subquery_df, use_container_width=True)            
        # st.write(subquery_df)
        # st.write(subquery_tags)

    st.markdown('''## Market Trends
        Information obtained from Google Trends
        
        This shows the most popular searchs at Google.
    ''')
    trends = st.button('Get market Trends!')
    if trends:
        trendcapt = TrendCapturer(['ukraine', 'russia', 'united_states', 'germany', 'vietnam']) #the selection of the markets is based on our user concentration
        raw_trends = trendcapt.main_searches()

        st.dataframe(trendcapt.grouped_main_searches_suggestions(trendcapt.main_searches_suggestions(raw_trends)))


if section == 'Transfers':
    
    filter_dict = {}

    event_values = ['Initialised',
    'ExtrinsicSuccess',
    'Transfer',
    'EndowedTransfer',
    'Reserved',
    'EndowedBoughtCompleteSet',
    'BoughtCompleteSet',
    'Transferred',
    'EndowedTransferred']

    account_id = st.sidebar.text_input('Account ID')

    event = st.sidebar.multiselect(
        'Event',
        event_values)

    asset_type = st.sidebar.multiselect(
        'Assets',
        ['ZTG', 'Markets', 'Pools'])

    if 'Markets' in asset_type:
        market_id = st.sidebar.text_input('Market ID (will show all markets by default)')
    
    if 'Pools' in asset_type:
        pool_id = st.sidebar.number_input('Pool ID (will show all pools by default)')
    
    filter = st.sidebar.button('Search!')

    if filter:
        filter_dict = {}
        if len(account_id) >0:
            filter_dict['account'] = {
                                        'id_eq': account_id
                                    }
                        
        if len(event) > 0:
            filter_dict['event_eq'] = event

        if 'Markets' in asset_type:
            if market_id:
                mkt_value = f'[{market_id},'
                filter_dict['assetId_contains'] = mkt_value
            else:
                filter_dict['assetId_contains'] = 'categoricalOutcome'
        
        if 'Pools' in asset_type:
            if pool_id:
                pool_value = ':'+pool_id+'}'
                filter_dict['assetId_contains'] = pool_value
            else:
                filter_dict['assetId_contains'] = 'poolShare'
        
        if len(filter_dict.keys()) > 0:
            filter_str = str(filter_dict)
            query_condition = f'(where: {filter_str})'
            query = '''
                    query MyQuery {
                        historicalAssetBalances'''+query_condition+''' {
                            createdAt
                            event  
                            amount
                            assetId
                            accountId
                            createdById
                            balance
                            blockNumber      
                        }
                    }
                '''
        else:
            query = '''
                    query MyQuery {
                        historicalAssetBalances {
                            createdAt
                            event  
                            amount
                            assetId
                            accountId
                            createdById
                            balance
                            blockNumber      
                        }
                    }
                '''

        result = run_query(zeitgeist_uri, query, status_code)
        clean_result = result['data']['historicalAssetBalances']
        
        final_df = pd.DataFrame()
        index_val= 0

        for r in clean_result:
            index_list = [index_val]
            temp = pd.DataFrame(r, index = index_list)
            temp['amount'] = round(int(temp['amount'])/10000000000, 2)
            temp['balance'] = round(int(temp['balance'])/10000000000, 2)

            final_df = final_df.append(temp)
            index_val += 1

        max_amount = float(final_df['amount'].max())
        min_amount = float(final_df['amount'].min())

        values = st.slider(
            'Select a range of values',
            min_value=min_amount, max_value=max_amount, step=0.1)
        
        st.write(max_amount)

        st.dataframe(final_df, 900)
    else:
        st.info('Filter and Search!')

if section == 'User Value':
    pass
    

