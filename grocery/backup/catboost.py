from datetime import date, timedelta
import calendar as ca
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder,LabelEncoder
import lightgbm as lgb
import gc

print('Loading Data')
df_train = pd.read_csv(
    'input/train.csv', usecols=[1, 2, 3, 4, 5],
    dtype={'onpromotion': bool},
    converters={'unit_sales': lambda u: np.log1p(
        float(u)) if float(u) > 0 else 0},
    parse_dates=["date"],
    skiprows=range(1, 86458909)  
)
item_nbr_u = df_train[df_train.date>pd.datetime(2017,8,10)].item_nbr.unique()

df_test = pd.read_csv(
    "input/test.csv", usecols=[0, 1, 2, 3, 4],
    dtype={'onpromotion': bool},
    parse_dates=["date"]  # , date_parser=parser
)

df_stores = pd.read_csv(
    "input/stores.csv"
)

df_items = pd.read_csv(
    "input/items.csv",
)

df_oil = pd.read_csv(
    "input/oil.csv",
    parse_dates=["date"] 
)

df_transactions = pd.read_csv(
    "input/transactions_with_pred.csv",
    parse_dates=["date"] 
)


items = pd.read_csv(
    "input/items.csv",
).set_index("item_nbr")

df2017 = df_train.loc[df_train.date>=pd.datetime(2017,2,9)]

df_2017 = df_train.loc[df_train.date>=pd.datetime(2017,2,9)]
del df_train
gc.collect()

# create promo feature
promo_2017_train = df_2017.set_index(
    ["store_nbr", "item_nbr", "date"])[["onpromotion"]].unstack(
        level=-1).fillna(False)
promo_2017_train.columns = promo_2017_train.columns.get_level_values(1)
promo_2017_test = df_test.set_index(
    ["store_nbr", "item_nbr", "date"])[["onpromotion"]].unstack(level=-1).fillna(False)
promo_2017_test.columns = promo_2017_test.columns.get_level_values(1)
promo_2017_test = promo_2017_test.reindex(promo_2017_train.index).fillna(False)
promo_2017 = pd.concat([promo_2017_train, promo_2017_test], axis=1)
del promo_2017_test, promo_2017_train
gc.collect()

# create sales feature
df_2017 = df_2017.set_index(
    ["store_nbr", "item_nbr", "date"])[["unit_sales"]].unstack(
        level=-1).fillna(0)
df_2017.columns = df_2017.columns.get_level_values(1)
  
items =  df_items.set_index("item_nbr").reindex(df_2017.index.get_level_values(1))

#create store id feature
df_store = df2017.set_index(
    ["store_nbr", "item_nbr", "date"])[["store"]].unstack(
        level=-1).fillna(-1)
df_store.columns = df_store.columns.get_level_values(1)
df_store['store'] = df_store.max(axis=1)
df_store = df_store['store']
df_store_train2 = pd.get_dummies(df_store, columns=['store'], prefix='store', drop_first=True, sparse=True)
del df_store

# merge train,test with items
df_items_train = pd.merge(df2017, df_items, how='left', on=['item_nbr'])

# merge train,test with stores
df_stores_train = pd.merge(df2017, df_stores, how='left', on=['store_nbr'])

# merge train with items
df_items_train = pd.merge(df2017, df_items, how='left', on=['item_nbr'])

# merge train with stores
df_stores_train = pd.merge(df2017, df_stores, how='left', on=['store_nbr'])

# merge train,test with oil
df_oil_train = pd.merge(df2017, df_oil, how='left', on=['date'])
df_oil_test = pd.merge(df_test, df_oil, how='left', on=['date'])


# lable encoder for items and stores
def df_lbl_enc(df):
    for c in df.columns:
        if df[c].dtype == 'object':
            lbl = LabelEncoder()
            df[c] = lbl.fit_transform(df[c])
            print(c)
    return df

df_items_train = df_lbl_enc(df_items_train)
df_stores_train = df_lbl_enc(df_stores_train)

# create items one hot encoder feature
df_family_train = df_items_train.set_index(
    ["store_nbr", "item_nbr", "date"])[["family"]].unstack(
        level=-1).fillna(-1)
df_family_train.columns = df_family_train.columns.get_level_values(1)
df_class_train = df_items_train.set_index(
    ["store_nbr", "item_nbr", "date"])[["class"]].unstack(
        level=-1).fillna(-1)
df_class_train.columns = df_class_train.columns.get_level_values(1)
df_perishable_train = df_items_train.set_index(
    ["store_nbr", "item_nbr", "date"])[["perishable"]].unstack(
        level=-1).fillna(-1)
df_perishable_train.columns = df_perishable_train.columns.get_level_values(1)
df_family_train['family'] = df_family_train.max(axis=1)
df_class_train["class"] = df_class_train.max(axis=1)
df_perishable_train["perishable"] = df_perishable_train.max(axis=1)
df_family_train = df_family_train['family']
df_class_train = df_class_train["class"]
df_perishable_train = df_perishable_train["perishable"]
df_family_train2 = pd.get_dummies(df_family_train, columns=['family'], prefix='family', drop_first=True)
df_class_train2 = pd.get_dummies(df_class_train, columns=['class'], prefix='class', drop_first=True)
df_perishable_train2 = pd.get_dummies(df_perishable_train, columns=['perishable'], prefix='perishable', drop_first=True)

del df_items_train
gc.collect()

# create stores one hot encoder feature
df_city_train = df_stores_train.set_index(
    ["store_nbr", "item_nbr", "date"])[["city"]].unstack(
        level=-1).fillna(-1)
df_city_train.columns = df_city_train.columns.get_level_values(1)
df_state_train = df_stores_train.set_index(
    ["store_nbr", "item_nbr", "date"])[["state"]].unstack(
        level=-1).fillna(-1)
df_state_train.columns = df_state_train.columns.get_level_values(1)
df_type_train = df_stores_train.set_index(
    ["store_nbr", "item_nbr", "date"])[["type"]].unstack(
        level=-1).fillna(-1)
df_type_train.columns = df_type_train.columns.get_level_values(1)
df_cluster_train = df_stores_train.set_index(
    ["store_nbr", "item_nbr", "date"])[["cluster"]].unstack(
        level=-1).fillna(-1)
df_cluster_train.columns = df_cluster_train.columns.get_level_values(1)

df_city_train['city'] = df_city_train.max(axis=1)
df_state_train["state"] = df_state_train.max(axis=1)
df_type_train["type"] = df_type_train.max(axis=1)
df_cluster_train["cluster"] = df_cluster_train.max(axis=1)

df_city_train = df_city_train['city']
df_state_train = df_state_train["state"]
df_type_train = df_type_train["type"]
df_cluster_train = df_cluster_train["cluster"]

df_city_train2 = pd.get_dummies(df_city_train, columns=['city'], prefix='city', drop_first=True)
df_state_train2 = pd.get_dummies(df_state_train, columns=['state'], prefix='state', drop_first=True)
df_type_train2 = pd.get_dummies(df_type_train, columns=['type'], prefix='type', drop_first=True)
df_cluster_train2 = pd.get_dummies(df_cluster_train, columns=['cluster'], prefix='cluster', drop_first=True)

del df_stores_train
gc.collect()

# create oil feature
df_oil_train = df_oil_train.set_index(
    ["store_nbr", "item_nbr", "date"])[["dcoilwtico"]].unstack(
        level=-1).fillna(method='bfill')
df_oil_train.columns = df_oil_train.columns.get_level_values(1)
df_oil_test = df_oil_test.set_index(
    ["store_nbr", "item_nbr", "date"])[["dcoilwtico"]].unstack(
        level=-1).fillna(method='bfill')
df_oil_test.columns = df_oil_test.columns.get_level_values(1)
df_oil_test = df_oil_test.reindex(df_oil_train.index).fillna(method='bfill')
df_oil = pd.concat([df_oil_train, df_oil_test], axis=1)

del df_oil_train,df_oil_test
gc.collect()

def get_timespan(df, dt, minus, periods, freq='D'):
    return df[pd.date_range(dt - timedelta(days=minus), periods=periods, freq=freq)]

def get_nearwd(date,b_date):
    date_list = pd.date_range(date-timedelta(112),periods=17,freq='7D').date
    result = date_list[date_list<=b_date][-1]
    return result


def prepare_dataset(t2017, is_train=True):
    X = pd.DataFrame({
#        "trans_3_2017":  get_timespan(df_transactions_train, t2017, 3, 3).mean(axis=1).values, 
#        "trans_7_2017":  np.log(get_timespan(df_transactions_train, t2017, 7, 7).mean(axis=1).values),   
#        "trans_14_2017":  np.log(get_timespan(df_transactions_train, t2017, 14, 14).mean(axis=1).values),   
#        "trans_30_2017":  np.log(get_timespan(df_transactions_train, t2017, 30, 30).mean(axis=1).values),   
#        "trans_60_2017":  get_timespan(df_transactions_train, t2017, 60, 60).mean(axis=1).values,         
#        "trans_140_2017":  get_timespan(df_transactions_train, t2017, 140, 140).mean(axis=1).values, 
#        "trans_3_2017_median":  get_timespan(df_transactions_train, t2017, 3, 3).median(axis=1).values, 
#        "trans_7_2017_median":  get_timespan(df_transactions_train, t2017, 7, 7).median(axis=1).values,   
#        "trans_14_2017_median":  get_timespan(df_transactions_train, t2017, 14, 14).median(axis=1).values,   
#        "trans_30_2017_median":  get_timespan(df_transactions_train, t2017, 30, 30).median(axis=1).values,   
#        "trans_60_2017_median":  get_timespan(df_transactions_train, t2017, 60, 60).median(axis=1).values,         
            
        "day_1_2017": get_timespan(df_2017, t2017, 1, 1).values.ravel(),
             
        "mean_3_2017": get_timespan(df_2017, t2017, 3, 3).mean(axis=1).values,
        "mean_7_2017": get_timespan(df_2017, t2017, 7, 7).mean(axis=1).values,
        "mean_14_2017": get_timespan(df_2017, t2017, 14, 14).mean(axis=1).values,
        "mean_28_2017": get_timespan(df_2017, t2017, 28, 28).mean(axis=1).values,
        "mean_56_2017": get_timespan(df_2017, t2017, 56, 56).mean(axis=1).values,
        "mean_112_2017": get_timespan(df_2017, t2017, 112, 112).mean(axis=1).values,
        "std_7_2017": get_timespan(df_2017, t2017, 7, 7).std(axis=1).values,
        "std_14_2017": get_timespan(df_2017, t2017, 14, 14).std(axis=1).values,
        "std_28_2017": get_timespan(df_2017, t2017, 28, 28).std(axis=1).values,
 
        "median_3_2017": get_timespan(df_2017, t2017, 3, 3).median(axis=1).values,
        "median_7_2017": get_timespan(df_2017, t2017, 7, 7).median(axis=1).values,
        "median_14_2017": get_timespan(df_2017, t2017, 14, 14).median(axis=1).values,
        "median_28_2017": get_timespan(df_2017, t2017, 28, 28).median(axis=1).values,
        "median_56_2017": get_timespan(df_2017, t2017, 56, 56).median(axis=1).values,
        "median_112_2017": get_timespan(df_2017, t2017, 112, 112).median(axis=1).values,
        "max_3_2017": get_timespan(df_2017, t2017, 3, 3).max(axis=1).values,
        "max_7_2017": get_timespan(df_2017, t2017, 7, 7).max(axis=1).values, 
        "max_14_2017": get_timespan(df_2017, t2017, 14, 14).max(axis=1).values,
#        "max_30_2017": get_timespan(df_2017, t2017, 30, 30).max(axis=1).values,            
        "min_3_2017": np.nan_to_num(get_timespan(df_2017, t2017, 3, 3)[get_timespan(df_2017, t2017, 3, 3) > 0].min(axis=1).values),
        "min_7_2017": np.nan_to_num(get_timespan(df_2017, t2017, 7, 7)[get_timespan(df_2017, t2017, 7, 7) > 0].min(axis=1).values),
        "min_14_2017": np.nan_to_num(get_timespan(df_2017, t2017, 14, 14)[get_timespan(df_2017, t2017, 14, 14) > 0].min(axis=1).values),
#        "min_30_2017": np.nan_to_num(get_timespan(df_2017, t2017, 30, 30)[get_timespan(df_2017, t2017, 30, 30) > 0].min(axis=1).values),
#        "range_3_2017": get_timespan(df_2017, t2017, 3, 3).max(axis=1).values - np.nan_to_num(get_timespan(df_2017, t2017, 3, 3)[get_timespan(df_2017, t2017, 3, 3) > 0].min(axis=1).values),
#        "range_7_2017": get_timespan(df_2017, t2017, 7, 7).max(axis=1).values - np.nan_to_num(get_timespan(df_2017, t2017, 7, 7)[get_timespan(df_2017, t2017, 7, 7) > 0].min(axis=1).values), 
#        "range_14_2017": get_timespan(df_2017, t2017, 14, 14).max(axis=1).values - np.nan_to_num(get_timespan(df_2017, t2017, 14, 14)[get_timespan(df_2017, t2017, 14, 14) > 0].min(axis=1).values),
#        "range_30_2017": get_timespan(df_2017, t2017, 30, 30).max(axis=1).values - np.nan_to_num(get_timespan(df_2017, t2017, 30, 30)[get_timespan(df_2017, t2017, 30, 30) > 0].min(axis=1).values),            
 #       "per25_3_2017": get_timespan(df_2017, t2017, 3, 3).quantile(.25, axis=1).values,        
 #       "per25_7_2017": get_timespan(df_2017, t2017, 7, 7).quantile(.25, axis=1).values, 
            

        "promo_14_2017": get_timespan(promo_2017, t2017, 14, 14).sum(axis=1).values,
        "promo_28_2017": get_timespan(promo_2017, t2017, 28, 28).sum(axis=1).values,             
        "promo_56_2017": get_timespan(promo_2017, t2017, 56, 56).sum(axis=1).values,
        "promo_112_2017": get_timespan(promo_2017, t2017, 112, 112).sum(axis=1).values,
        "unpromo_16aftsum_2017":(1-get_timespan(promo_2017, t2017+timedelta(16), 16, 16)).iloc[:,1:].sum(axis=1).values, 
        })

    for i in range(16):
        X["oil_{}".format(i)] = df_oil[
            t2017 + timedelta(days=i)].values.astype(np.float32)         
        X["promo_{}".format(i)] = promo_2017[
            t2017 + timedelta(days=i)].values.astype(np.uint8)
        for j in [14,28,56,112]:  
            X["aft_promo_{}{}".format(i,j)] = (promo_2017[
                t2017 + timedelta(days=i)]-1).values.astype(np.uint8)
            X["aft_promo_{}{}".format(i,j)] = X["aft_promo_{}{}".format(i,j)]\
                                        *X['promo_{}_2017'.format(j)]

        if i ==15:
            X["bf_unpromo_{}".format(i)]=0
        else:
            X["bf_unpromo_{}".format(i)] = (1-get_timespan(
                    promo_2017, t2017+timedelta(16), 16-i, 16-i)).iloc[:,1:].sum(
                            axis=1).values / (15-i) * X['promo_{}'.format(i)]

    for i in range(7):
        X['mean_4_dow{}_2017'.format(i)] = get_timespan(df_2017, t2017, 28-i, 4, freq='7D').mean(axis=1).values
        X['median_4_dow{}_2017'.format(i)] = get_timespan(df_2017, t2017, 28-i, 4, freq='7D').median(axis=1).values
     
        X['mean_8_dow{}_2017'.format(i)] = get_timespan(df_2017, t2017, 56-i, 8, freq='7D').mean(axis=1).values
        X['median_8_dow{}_2017'.format(i)] = get_timespan(df_2017, t2017, 56-i, 8, freq='7D').median(axis=1).values
        
        X['mean_16_dow{}_2017'.format(i)] = get_timespan(df_2017, t2017, 112-i, 16, freq='7D').mean(axis=1).values
        X['median_16_dow{}_2017'.format(i)] = get_timespan(df_2017, t2017, 112-i, 16, freq='7D').median(axis=1).values

        date = get_nearwd(t2017+timedelta(i),t2017)
        ahead = (t2017-date).days
        if ahead!=0:
            X['ahead0_mean_{}'.format(i)] = get_timespan(df_2017, date+timedelta(ahead), ahead, ahead).mean(axis=1).values
            X['ahead7_mean_{}'.format(i)] = get_timespan(df_2017, date+timedelta(ahead), ahead+7, ahead+7).mean(axis=1).values
         
        X["day_1_2017_{}1".format(i)]= get_timespan(df_2017, date, 1, 1).values.ravel()
        X["day_1_2017_{}2".format(i)]= get_timespan(df_2017, date-timedelta(7), 1, 1).values.ravel()        
        for m in [3,7,14,28,56,112]:
            X["mean_{}_2017_{}1".format(m,i)]= get_timespan(df_2017, date,m, m).\
                mean(axis=1).values   
            X["mean_{}_2017_{}2".format(m,i)]= get_timespan(df_2017, date-timedelta(7),m, m).\
                mean(axis=1).values
                
    for c in df_family_train2.columns:
        X[c] = df_family_train2[c].values
    for c in df_class_train2.columns:
        X[c] = df_class_train2[c].values
    for c in df_perishable_train2.columns:
        X[c] = df_perishable_train2[c].values        

    for c in df_store_train2.columns:
        X[c] = df_store_train2[c].values 
    for c in df_city_train2.columns:
        X[c] = df_city_train2[c].values
    for c in df_state_train2.columns:
        X[c] = df_state_train2[c].values
    for c in df_type_train2.columns:
        X[c] = df_type_train2[c].values
    for c in df_cluster_train2.columns:
        X[c] = df_cluster_train2[c].values        
        
    if is_train:
        y = df_2017[
            pd.date_range(t2017, periods=16)
        ].values
        return X, y
    return X
    
print("Preparing dataset...")

t2017 = date(2017, 6, 14)
X_l, y_l = [], []
for i in range(6):
    delta = timedelta(days=7 * i)
    X_tmp, y_tmp = prepare_dataset(
        t2017 + delta
    )
    X_l.append(X_tmp)
    y_l.append(y_tmp)
X_train = pd.concat(X_l, axis=0)
y_train = np.concatenate(y_l, axis=0)
del X_l, y_l

X_val, y_val = prepare_dataset(date(2017, 7, 26))
X_test = prepare_dataset(date(2017, 8, 16), is_train=False)

gc.collect()

from catboost import Pool, CatBoostRegressor

print("Training and predicting catboost models...")

MAX_ROUNDS = 3000
val_pred = []
test_pred = []
cate_vars = []
for i in range(16):
    print("=" * 50)
    print("Step %d" % (i+1))
    print("=" * 50)
    model = CatBoostRegressor(
        iterations=MAX_ROUNDS, 
        learning_rate=0.03,
        depth=6, 
        l2_leaf_reg=3,
        loss_function='RMSE',
        eval_metric='RMSE',
        thread_count = 32,
        verbose = True,
        random_seed=0)
    train_pool = Pool(X_train, y_train[:, i],
        cat_features=cate_vars, weight=pd.concat([items["perishable"]] * 6) * 0.25 + 1) 
    eval_pool = Pool(X_val, y_val[:, i],
        cat_features=cate_vars, weight=pd.concat([items["perishable"]] * 1) * 0.25 + 1)     
    model.fit(train_pool, use_best_model=True, eval_set=eval_pool)

    val_pred.append(model.predict(X_val))
    test_pred.append(model.predict(X_test))
    
from sklearn import metrics
def NWRMSLE(y, pred, w):
    return metrics.mean_squared_error(y, pred, sample_weight=w)**0.5

n_public = 5 # Number of days in public test set
weights=pd.concat([items["perishable"]]) * 0.25 + 1
print("y_val")
print("Full validation mse:       ", NWRMSLE(
    y_val, np.array(val_pred).transpose(), weights) )
print("'Public' validation mse:   ", NWRMSLE(
    y_val[:,:n_public], np.array(val_pred).transpose()[:,:n_public], weights) )
print("'Private' validation mse:  ", NWRMSLE(
    y_val[:,n_public:], np.array(val_pred).transpose()[:,n_public:], weights) )

print("Making submission...")
y_test = np.array(test_pred).transpose()
df_preds = pd.DataFrame(
    y_test, index=df_2017.index,
    columns=pd.date_range("2017-08-16", periods=16)
).stack().to_frame("unit_sales")
df_preds.index.set_names(["store_nbr", "item_nbr", "date"], inplace=True)

submission = df_test.set_index(
    ["store_nbr", "item_nbr", "date"])[["id"]].join(df_preds, how="left").fillna(0).reset_index()
submission["unit_sales"] = np.clip(np.expm1(submission["unit_sales"]), 0, 10000)
submission.loc[~submission.item_nbr.isin(item_nbr_u),'unit_sales']=0
submission[['id','unit_sales']].to_csv('cat0114.csv', float_format='%.6f', index=None)    
