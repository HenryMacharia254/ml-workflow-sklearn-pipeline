# References
# https://github.com/jem1031/pandas-pipelines-custom-transformers
# http://zacstewart.com/2014/08/05/pipelines-of-featureunions-of-pipelines.html

import numpy as np
import pandas as pd
from functools import reduce

from sklearn.base import TransformerMixin, BaseEstimator
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import FunctionTransformer, StandardScaler, RobustScaler, MultiLabelBinarizer
from sklearn.impute import SimpleImputer 


class DFFunctionTransformer(TransformerMixin, BaseEstimator):
    # FunctionTransformer but for pandas DataFrames

    def __init__(self, *args, **kwargs):
        self.ft = FunctionTransformer(*args, **kwargs)

    def fit(self, X, y=None):
        # stateless transformer
        return self

    def transform(self, X):
        Xt = self.ft.transform(X)
        Xt = pd.DataFrame(Xt, index=X.index, columns=X.columns)
        return Xt


class DFFeatureUnion(TransformerMixin, BaseEstimator):
    # FeatureUnion but for pandas DataFrames

    def __init__(self, transformer_list):
        self.transformer_list = transformer_list

    def fit(self, X, y=None):
        for (name, t) in self.transformer_list:
            t.fit(X, y)
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xts = [t.transform(X) for _, t in self.transformer_list]
        Xunion = reduce(lambda X1, X2: pd.merge(X1, X2, left_index=True, right_index=True), Xts)
        return Xunion


class DFImputer(TransformerMixin, BaseEstimator):
    # Imputer but for pandas DataFrames
    '''Siraprapa W. :  Modify to accept constant strategy'''

    def __init__(self, strategy='mean',fill_value=None):
        self.strategy = strategy
        self.imp = None
        self.statistics_ = None
        self.fill_value = fill_value

    def fit(self, X, y=None):
        if self.strategy == 'constant':
            self.imp = SimpleImputer(strategy=self.strategy,fill_value=self.fill_value)
        else:
            self.imp = SimpleImputer(strategy=self.strategy)
            
        self.imp.fit(X)
        self.statistics_ = pd.Series(self.imp.statistics_, index=X.columns)
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Ximp = self.imp.transform(X)
        Xfilled = pd.DataFrame(Ximp, index=X.index, columns=X.columns)
        return Xfilled


class DFStandardScaler(TransformerMixin, BaseEstimator):
    # StandardScaler but for pandas DataFrames

    def __init__(self):
        self.ss = None
        self.mean_ = None
        self.scale_ = None

    def fit(self, X, y=None):
        self.ss = StandardScaler()
        self.ss.fit(X)
        self.mean_ = pd.Series(self.ss.mean_, index=X.columns)
        self.scale_ = pd.Series(self.ss.scale_, index=X.columns)
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xss = self.ss.transform(X)
        Xscaled = pd.DataFrame(Xss, index=X.index, columns=X.columns)
        return Xscaled


class DFRobustScaler(TransformerMixin, BaseEstimator):
    # RobustScaler but for pandas DataFrames

    def __init__(self):
        self.rs = None
        self.center_ = None
        self.scale_ = None

    def fit(self, X, y=None):
        self.rs = RobustScaler()
        self.rs.fit(X)
        self.center_ = pd.Series(self.rs.center_, index=X.columns)
        self.scale_ = pd.Series(self.rs.scale_, index=X.columns)
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xrs = self.rs.transform(X)
        Xscaled = pd.DataFrame(Xrs, index=X.index, columns=X.columns)
        return Xscaled


class ColumnExtractor(TransformerMixin, BaseEstimator):

    def __init__(self, cols):
        self.cols = cols

    def fit(self, X, y=None):
        # stateless transformer
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xcols = X[self.cols]
        return Xcols


class ZeroFillTransformer(TransformerMixin, BaseEstimator):

    def fit(self, X, y=None):
        # stateless transformer
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xz = X.fillna(value=0)
        return Xz


class Log1pTransformer(TransformerMixin, BaseEstimator):

    def fit(self, X, y=None):
        # stateless transformer
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xlog = np.log1p(X)
        return Xlog


class DateFormatter(TransformerMixin, BaseEstimator):

    def fit(self, X, y=None):
        # stateless transformer
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xdate = X.apply(pd.to_datetime,errors='coerce')
        return Xdate


class DateDiffer(TransformerMixin, BaseEstimator):

    def fit(self, X, y=None):
        # stateless transformer
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        beg_cols = X.columns[:-1]
        end_cols = X.columns[1:]
        Xbeg = X[beg_cols].as_matrix()
        Xend = X[end_cols].as_matrix()
        Xd = (Xend - Xbeg) / np.timedelta64(1, 'D')
        diff_cols = ['->'.join(pair) for pair in zip(beg_cols, end_cols)]
        Xdiff = pd.DataFrame(Xd, index=X.index, columns=diff_cols)
        return Xdiff


class DummyTransformer(TransformerMixin, BaseEstimator):

    def __init__(self):
        self.dv = None

    def fit(self, X, y=None):
        # assumes all columns of X are strings
        Xdict = X.to_dict(orient='records')
        self.dv = DictVectorizer(sparse=False)
        self.dv.fit(Xdict)
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xdict = X.to_dict(orient='records')
        Xt = self.dv.transform(Xdict)
        cols = self.dv.get_feature_names_out()
        Xdum = pd.DataFrame(Xt, index=X.index, columns=cols)
        # drop column indicating NaNs
        nan_cols = [c for c in cols if '=' not in c]
        Xdum = Xdum.drop(nan_cols, axis=1)
        return Xdum


class MultiEncoder(TransformerMixin, BaseEstimator):
    # Multiple-column MultiLabelBinarizer for pandas DataFrames

    def __init__(self, sep=','):
        self.sep = sep
        self.mlbs = None

    def _col_transform(self, x, mlb):
        cols = [''.join([x.name, '=', c]) for c in mlb.classes_]
        xmlb = mlb.transform(x)
        xdf = pd.DataFrame(xmlb, index=x.index, columns=cols)
        return xdf

    def fit(self, X, y=None):
        Xsplit = X.applymap(lambda x: x.split(self.sep))
        self.mlbs = [MultiLabelBinarizer().fit(Xsplit[c]) for c in X.columns]
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xsplit = X.applymap(lambda x: x.split(self.sep))
        Xmlbs = [self._col_transform(Xsplit[c], self.mlbs[i])
                 for i, c in enumerate(X.columns)]
        Xunion = reduce(lambda X1, X2: pd.merge(X1, X2, left_index=True, right_index=True), Xmlbs)
        return Xunion


class StringTransformer(TransformerMixin, BaseEstimator):

    def fit(self, X, y=None):
        # stateless transformer
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xstr = X.applymap(str)
        return Xstr


class ClipTransformer(TransformerMixin, BaseEstimator):

    def __init__(self, a_min, a_max):
        self.a_min = a_min
        self.a_max = a_max

    def fit(self, X, y=None):
        # stateless transformer
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xclip = np.clip(X, self.a_min, self.a_max)
        return Xclip


class AddConstantTransformer(TransformerMixin, BaseEstimator):

    def __init__(self, c=1):
        self.c = c

    def fit(self, X, y=None):
        # stateless transformer
        return self

    def transform(self, X):
        # assumes X is a DataFrame
        Xc = X + self.c
        return Xc


class Clip2NaN(TransformerMixin, BaseEstimator):
    '''Siraprapa W. anything out of scope will be set to nan'''

    def __init__(self,min=0,max=100):
        # this is where you can init internal variable
        self.min=min
        self.max=max

    def fit(self, X, y=None):
        # this is what happend when .fit is invoked
        return self

    def transform(self, X):
        # this is what happend when .tranform is invoked
        # Assume X is pandas
        Xclip = X.apply(lambda x: x if self.min<=x.item()<=self.max else np.nan,axis=1)
        return Xclip

class PredictProba(TransformerMixin, BaseEstimator):
    '''model.predict_proba'''

    def __init__(self,model):
        self.model = model

    def fit(self,*args, **kwargs):
        #expecting X, and y
        self.model.fit(*args, **kwargs)
        return self

    def transform(self,X,**transform_params):
        return self.model.predict_proba(X)
    
#