import requests 
import json
import numpy.random as random
random.seed()
import datetime
# for each election in the simulation,
# pick a temperature from a normal distribution
temperature_mean = 0
temperature_stdev = 0.1
# for each state in each election,
# probability offset is chosen from normal distribution
# with mean at election temperature
state_offset_stdev = 0.1
# how many simulations to run
num_trials = 100000

def request_json (url):
    return json.loads(
           requests.get(url, headers={
            'Accept':'application/json'}).content)

def predictit (ticker):
    return request_json('https://www.predictit.org/api/marketdata/ticker/' + ticker)

def market (state_abbreviation, party):
    api_res = predictit('DEM.'+state_abbreviation+'.USPREZ16')
    contracts = api_res['Contracts']
    contract = filter(lambda c: c['ShortName']==party, contracts)[0]
    return contract

def probability (state_abbreviation, party=None):
    # Average both party markets by default
    if (party is None):
       return (probability(state_abbreviation, 'Democratic') +
              probability(state_abbreviation, 'Republican'))/2
    mkt = market(state_abbreviation, party)
    # For republican markets, get the No cost
    if (party=='Republican'):
       sell = mkt['BestSellNoCost']
       buy = mkt['BestBuyNoCost']
    # For democratic markets, get the "Yes cost
    elif (party=='Democratic'):
       sell = mkt['BestSellYesCost']
       buy = mkt['BestBuyYesCost']
    # If the spread is > 5
    spread = buy-sell
    if (sell > 5):
       # Just use the last trade price
       return mkt['LastTradePrice']
    return (sell+buy)/2.0


def predictwise_states (col):
    table = json.loads(requests.get('http://table-cache1.predictwise.com/latest/table_1551.json').content)
    def predictwise_state (row):
        return {'name': row[0],
                'probability': float(int(row[col].split(' ')[0]))/100.0,
                'delegates': int(row[-1])}
    return map(predictwise_state, table['table'])

# debiased market probabilties
debiased_states = predictwise_states(2)
# predictwise states
pw_states = predictwise_states(1)

def state (abbrev, delegates):
    return {"abbreviation": abbrev,
           "delegates": delegates,
           "probability": probability(abbrev),}

states_delegates = {'AL':9, 'AK':3, 'AZ':11, 'AR':6, 'CA':55, 'CO':9, 'CT':7, 'DC':3, 'DE':3, 'FL':29, 'GA':16, 'HI':4, 'ID':4, 'IL':20, 'IN':11, 'IA':6, 'KS':6, 'KY':8, 'LA':8, 'ME':4, 'MD':10, 'MA':11, 'MI':16, 'MN':10, 'MS':6, 'MO':10, 'MT':3, 'NE':5, 'NV':6, 'NH':4, 'NJ':14, 'NM':5, 'NY':29, 'NC':15, 'ND':3, 'OH':18, 'OK':7, 'OR':7, 'PA':20, 'RI':4, 'SC':9, 'SD':3, 'TN':11, 'TX':38, 'UT':6, 'VT':3, 'VA':13, 'WA':12, 'WV':5, 'WI':10, 'WY':3,} 
print 'sanity check - delegates add up to 538?', 538 == sum([val for key, val in states_delegates.iteritems()])

states = [state(key,val) for key, val in states_delegates.iteritems()]

def normal (center, scale):
    return random.normal(center,scale)

def bound (probability):
    if (probability>1):
        return 1
    elif (probability<0):
        return 0
    return probability


def decide (probability):
    return random.random()<probability
    
def election_holder (temperature):
    '''
    Returns fn (state), which simulates an election in that state,
    and returns a number of delegates allocated to Dems (0 if loss).
    '''
    def hold_election (state):
        probability_offset = normal(temperature, state_offset_stdev)
        probability = bound(state['probability'] + probability_offset)
        return state['delegates'] * decide(probability)
    return hold_election

def simulate_election (states):
    '''
    Return number of delegates for Clinton.
    '''
    temperature = normal(temperature_mean, temperature_stdev)
    return sum(map(election_holder(temperature), states))
    
def simulate_elections (trials, states):
    ts = [states for i in range(trials)]
    return map(simulate_election, ts)

def percent_winning (simulations):
    winning = lambda delegates: delegates > 268
    return float(len(filter(winning, simulations)))/float(num_trials)

# predicted market price simulations
simulations = simulate_elections(num_trials, states)
predicted_market_price = percent_winning(simulations)
print 'predicted market price:',  predicted_market_price

simulations = simulate_elections(num_trials, debiased_states)
predicted_prob_debiased = percent_winning(simulations)*100
print 'predicted Clinton (debiased market probabilities):', predicted_prob_debiased, '%'

simulations = simulate_elections(num_trials, pw_states)
predicted_prob_pw = percent_winning(simulations)*100
print 'predicted Clinton (PredictWise state probabilities):', predicted_prob_pw, '%'

# overvalued clinton shares
print 'uncertain clinton odds'
unlikely = filter(lambda s: s['probability']<0.7 and s['probability']>0.2, states)
print map(lambda s: (s['abbreviation'], s['probability']), unlikely)

# fivethirtyeight
forecastURL = 'http://projects.fivethirtyeight.com/2016-election-forecast/US.json'
forecast = requests.get(forecastURL).json()
clinton538 = forecast['forecasts']['latest']['D']['models']['polls']['winprob']
print '538', clinton538

# predictwise
forecastURL = 'http://table-cache1.predictwise.com/history/table_1032.json'
forecast = requests.get(forecastURL).json()
predictwise = forecast['latest']
def dem (r):
    return r[0]=='Democratic'
clinton_pw = float(filter(dem, predictwise)[0][1].split(' ')[0])
print 'pw', clinton_pw

# write to CSV
row = ','.join([
    datetime.datetime.now().isoformat(),
    str(predicted_market_price),
    str(predicted_prob_debiased),
    str(predicted_prob_pw),
    str(clinton538), 
    str(clinton_pw),
    ])+'\n'
fd = open('predictions.csv','a')
fd.write(row)
fd.close()
