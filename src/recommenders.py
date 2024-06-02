from typing import List
import pandas as pd
from sklearn.cluster import KMeans
from scipy.sparse import csr_matrix
import numpy as np
from tqdm import tqdm
from sklearn.preprocessing import Normalizer, StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer, KNNImputer
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, fpmax, fpgrowth, association_rules

class RuleBasedRecommender:
    """
    Rule-based recommender class.
    This class is used for rule-based recommendation.
    """


class Data:
    def __init__(self,data_dir:str="ml-latest-small",
                  test_percent:float=0.2,
                  imputer=SimpleImputer(strategy="mean"),
                  preprocessors:List=[StandardScaler()],
                  seed:int=124) -> None:
        """
        Data class for processing and preparing data for clustering-based recommendation.
        
        Parameters:
        - data_dir (str): Directory path where the data files are located.
        - test_percent (float): Percentage of data to be used for testing.
        - imputer: Imputer object to fill NaN values in the data table.
        - preprocessors: List of preprocessor objects to apply on the data table.
        - seed (int): Random seed for reproducibility.
        """
        
        self.imputer = imputer
        self.preprocessors = preprocessors

        self.unprocessed_data = pd.merge(pd.read_csv(f'{data_dir}/{"movies"}.csv'),
                             pd.read_csv(f'{data_dir}/{"ratings"}.csv'),
                             on='movieId')
        
        self.unprocessed_data = self.unprocessed_data[["movieId", "genres", "userId", "rating"]]
        self.unprocessed_data["genres"] = self.unprocessed_data["genres"].str.split("|")
        self.unprocessed_data = self.unprocessed_data.explode("genres")
        

        self.movie_genres = self.unprocessed_data[["movieId", "genres"]].drop_duplicates()
        self.train_data, self.test_data = train_test_split(
                    self.unprocessed_data, test_size=test_percent, random_state=seed)
        
        self.train_data_table_for_clustering = self.train_data.pivot_table(index='userId', 
                                           columns='genres', values='rating',aggfunc="mean")
        
        #impute NaN values
        imputed_data = imputer.fit_transform(self.train_data_table_for_clustering)
        self.train_data_table_for_clustering = pd.DataFrame(imputed_data, 
                                                            columns=self.train_data_table_for_clustering.columns, 
                                                            index=self.train_data_table_for_clustering.index)

        #apply preprocessors sequentially
        preprocessed_data = self.train_data_table_for_clustering
        for preprocessor in self.preprocessors:
            preprocessed_data = preprocessor.fit_transform(preprocessed_data)

        #these names are getting a bit long but well... everything for clarity 
        self.train_data_table_for_clustering_normalized = pd.DataFrame(preprocessed_data,
                                                                      columns=self.train_data_table_for_clustering.columns,
                                                                      index=self.train_data_table_for_clustering.index)





class ClusteringBasedRecommender:
    def __init__(self, apriori:bool, data:pd.DataFrame,
                 data_unnormalized:pd.DataFrame,
                 movie_genres:pd.DataFrame,
                 clusterer=KMeans(10, random_state=124)) -> None:
        """
        Clustering-based recommender class.
        This class is used for clustering-based recommendation.
        
        Parameters:
        - data (pd.DataFrame): Data table used for clustering.
        - data_unnormalized (pd.DataFrame): Unnormalized data table used for prediction.
        - movie_genres (pd.DataFrame): Data table containing movie genres.
        - clusterer: Clustering algorithm object to be used.
        """
        self.if_apriori = apriori
        self.data_table = data
        self.data_table_unnormalized = data_unnormalized

        self.movie_genres = movie_genres
        self.clusterer = clusterer
        self.clusters = None
        
    def train(self) -> None:
        """
        Train the clustering-based recommender model.
        This method performs clustering on the data table and assigns clusters to each data point.
        if aprior=True, also includes apriori
        """
        self.clusters = self.clusterer.fit_predict(self.data_table)
        self.data_table['cluster'] = self.clusters
        data_to_apriori = self.data_table
        
        if self.if_apriori == True:
            self.counter = 0
            obj = Apriori(data_to_apriori)
            self.rules = obj.give_rules()
            self.confidence_rules =  obj.give_confidence()
    def predict(self, user_id:int, movie_id:int) -> float:
        """
        Predict the rating for a given user and movie.
        
        Parameters:
        - user_id (int): ID of the user.
        - movie_id (int): ID of the movie.
        
        Returns:
        - float: Predicted rating for the user and movie.
        """
        user_cluster = self.clusters[user_id-1]
        movie_genres = self.movie_genres[self.movie_genres['movieId'] == movie_id]['genres'].values

        users_in_cluster = self.data_table[self.data_table['cluster'] == user_cluster].index
        genre_ratings = self.data_table_unnormalized.loc[users_in_cluster, movie_genres].mean(axis=1).mean()
        
        if self.if_apriori != True:
            return genre_ratings
        id_format = "userId_{}".format(user_id)
        movie_id_str = str(movie_id)
        confidence = 0
        for j in range(0,12,1):
             rait = "rating_{}".format(j/2)
             assosciation_1 = tuple(sorted([rait,movie_id_str]))
             if assosciation_1 in self.rules[user_cluster]:
                print(assosciation_1)
                self.counter += 1
                genre_ratings = j/2
                confidence = self.confidence_rules[user_cluster][assosciation_1]
        for j in range(0,12,1):
             rait = "rating_{}".format(j/2)
             assosciation_2 = tuple(sorted([rait,id_format]))
             if assosciation_2 in self.rules[user_cluster]:
                 print(assosciation_2)
                 self.counter += 1
                 if self.confidence_rules[user_cluster][assosciation_2] < confidence:
                    continue
                
                

                 genre_ratings = j/2
                 confidence = self.confidence_rules[user_cluster][assosciation_2]
             for genre in movie_genres:
                assosciation_3 = tuple(sorted([genre,rait]))
                if assosciation_3 in self.rules[user_cluster]:
                    print(assosciation_3)
                    self.counter += 1
                    if self.confidence_rules[user_cluster][assosciation_3] < confidence:
                        continue
                    self.counter += 1
                  
                  
                    genre_ratings = j/2
                    confidence = self.confidence_rules[user_cluster][assosciation_3]
                assosciation_4 = tuple(sorted([genre,rait,id_format]))
                if assosciation_4 in self.rules[user_cluster]:
                    print(assosciation_4)
                    if self.confidence_rules[user_cluster][assosciation_4] < confidence:
                        continue
                    self.counter += 1
                    genre_ratings = j/2
        # #possible
        return genre_ratings
    
class Apriori:
    def __init__(self,data_clustered,data_dir:str="ml-latest-small",
                  seed:int=124) -> None:
        self.unprocessed_data = pd.merge(pd.read_csv(f'{data_dir}/{"movies"}.csv'),
                             pd.read_csv(f'{data_dir}/{"ratings"}.csv'),
                             on='movieId')
        data_clustered =  data_clustered.reset_index()
        self.data_clustered = data_clustered[['cluster','userId']]
        self.data_to_apriori = pd.merge(self.unprocessed_data,self.data_clustered,on="userId")
        self.data_to_apriori["rating"] = self.data_to_apriori["rating"].apply(lambda x: f"rating_{x}")
        self.data_to_apriori["genres"] = self.data_to_apriori["genres"].str.split("|")
        self.data_to_apriori = self.data_to_apriori.explode("genres")
        # One-hot encode the genres
        self.data_to_apriori = pd.concat([self.data_to_apriori, 
                                           pd.get_dummies(self.data_to_apriori['genres'])], axis=1)
        # Drop the original genres column
        self.data_to_apriori.drop(columns=['genres'], inplace=True)
        genre_columns = [col for col in self.data_to_apriori.columns if col not in ['userId', 'movieId', 'rating','cluster']]
        self.rules_dict1 = {}
        self.rules_dict2 = {}
        grouped = self.data_to_apriori.groupby('cluster')

        for cluster,group in tqdm(grouped):
            transactions1= group.apply(lambda row: [f"userId_{row['userId']}", row['rating']] + \
                                             [genre for genre in genre_columns if row[genre] == 1], axis=1).tolist()
            
            transactions2 = group.apply(lambda row: [ row['rating'],row['movieId']], axis=1).tolist()
            transactions1 = [[str(elem) for elem in transaction] for transaction in transactions1]
            transactions2 = [[str(elem) for elem in transaction] for transaction in transactions2]
            te1 = TransactionEncoder()
            te2 = TransactionEncoder()
            te_ary1 = te1.fit(transactions1).transform(transactions1)
            te_ary2 = te2.fit(transactions2).transform(transactions2)
            self.encoded_data = pd.DataFrame(te_ary1, columns=te1.columns_)
            self.rules_dict1[cluster] = self.get_association_rules(self.encoded_data)
            self.encoded_data = pd.DataFrame(te_ary2, columns=te2.columns_)
            self.rules_dict2[cluster] = self.get_association_rules(self.encoded_data)
        

        self.all_rules = {}
        self.all_rules_confidence = {}
        # Iterate over self.rules_dict1 and self.rules_dict2
        for cluster, rules_df in self.rules_dict1.items():
            # Extract the rules as tuples (antecedent, consequent)
            rules_list = set([tuple(sorted(list(rule.antecedents) +list(rule.consequents)))
                               for rule in rules_df.itertuples()
                              if any('rating' in element for element in rule.consequents)])
            self.all_rules_confidence[cluster] = {tuple(sorted(list(rule.antecedents) +list(rule.consequents))):rule.confidence 
                                                  for rule in rules_df.itertuples()
                                                   if any('rating' in element for element in rule.consequents) }
            
            self.all_rules[cluster] = rules_list

        for cluster, rules_df in self.rules_dict2.items():
            # Extract the rules as tuples (antecedent, consequent)
            rules_list = set([tuple(sorted(list(rule.antecedents) +list(rule.consequents))) 
                              for rule in rules_df.itertuples()
                              if any('rating' in element for element in rule.consequents)])
            if self.all_rules[cluster] is not None:
                self.all_rules[cluster] = self.all_rules[cluster] | rules_list
                self.all_rules_confidence[cluster] = self.all_rules_confidence[cluster] | {tuple(sorted(list(rule.antecedents) +list(rule.consequents))):rule.confidence 
                                                                                           for rule in rules_df.itertuples() 
                                                                                           if any('rating' in element for element in rule.consequents)}
            else:
                self.all_rules[cluster] = rules_list
                self.all_rules_confidence[cluster] = {tuple(sorted(list(rule.antecedents) +list(rule.consequents))):rule.confidence 
                                                      for rule in rules_df.itertuples()
                                                       if any('rating' in element for element in rule.consequents) }
        # print(self.all_rules)
        # print(self.all_rules_confidence)

       
       
    def give_rules(self):
        return self.all_rules
    def give_confidence(self):
        return self.all_rules_confidence
       
        

        

    @staticmethod
    def get_association_rules(data, min_support=0.0005, metric="confidence", min_threshold=0.7):
        frequent_itemsets = apriori(data, min_support=min_support, use_colnames=True)
      
        print(len(frequent_itemsets))
        rules = association_rules(frequent_itemsets, metric=metric, min_threshold=min_threshold)
        return rules