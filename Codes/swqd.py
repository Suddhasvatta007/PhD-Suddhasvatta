# -*- coding: utf-8 -*-
"""SWQD.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Bgx0c8bQC7OuecDl26brF7QD4Lq5UTKs
"""

#mount data from G-drive
from google.colab import drive
drive.mount('/content/drive')

import pandas as pd
import numpy as np
import random
import warnings

#----------------------------------------------------------#
warnings.simplefilter(action='ignore', category=FutureWarning)

# From AM Raw Data -> Data Format that is in use
raw_data_file_path = 'RAW_DATA.xlsx'
raw_data_data = pd.read_excel(raw_data_file_path, sheet_name='Final')
total_number_of_specs_in_raw_data = 1848

SPEC_TO_TC_MAPPING = {}
SPEC_TO_BV_MAPPING = {}


for index, row in raw_data_data.iterrows():
  us_id = int(row['us_id'])
  ds_id = int(row['ds_id'])
  SPEC_TO_TC_MAPPING[(us_id, ds_id)] = SPEC_TO_TC_MAPPING.get((us_id, ds_id), 0) + int(row['tc_executiontime'])
  SPEC_TO_BV_MAPPING[(us_id, ds_id)] = int(row['us_businessvalue'])

#DATA PREPARATION STEP FOR AI-GA & RANDOM
df_spec_BV_tc_execTime = pd.DataFrame(columns=['Spec ID', 'BV', 'Total Test Exec Time', 'ds_id'])
Running_Spec_ID = 1
for index, row in SPEC_TO_TC_MAPPING.items():
  new_row = {
      'Spec ID': Running_Spec_ID,
      'BV': SPEC_TO_BV_MAPPING[index],
      'Total Test Exec Time': SPEC_TO_TC_MAPPING[index],
      'ds_id': index[1]
  }
  Running_Spec_ID = Running_Spec_ID + 1
  df_spec_BV_tc_execTime = pd.concat([df_spec_BV_tc_execTime, pd.DataFrame([new_row])], ignore_index=True)

df_spec_BV_tc_execTime.to_excel('RAW_DATA_To_SPEC_TC_Mapping.xlsx', index=False)

warnings.simplefilter(action='ignore', category=FutureWarning)

#---------------- CANDIDATE SET SELECTION & Regression Test Window -----------------------------#
NUMBER_OF_SPECS_SELECTED = 400 # How many random specs to be selected from raw data
REG_TIME_Percent = 0.25 # Amount of time from total needed time given for regression


#random_df_spec_BV_min_test_run = df_spec_BV_min_test_run.sample(n=NUMBER_OF_SPECS_SELECTED)
random_df_spec_BV_min_test_run = df_spec_BV_tc_execTime.sample(n=NUMBER_OF_SPECS_SELECTED, random_state=42)

TOTAL_BV_IN_RANDOMLY_SELECTED_SPECS = int(sum(random_df_spec_BV_min_test_run['BV']))
TOTAL_REGRESSION_TIME_IN_RANDOMLY_SELECTED_SPECS = int(sum(random_df_spec_BV_min_test_run['Total Test Exec Time']))
REGRESSION_TIME = TOTAL_REGRESSION_TIME_IN_RANDOMLY_SELECTED_SPECS * REG_TIME_Percent

#preparation for AI algorithms (BV, spec's total exec time)
candidate_set_array = [] # BV, Exec Time
for index, row in random_df_spec_BV_min_test_run.iterrows():
  if int(row['BV']) != 0:
    candidate_set_array.append((row['BV'], int(row['Total Test Exec Time'])))
candidate_set = pd.DataFrame(candidate_set_array, columns=['BV', 'Total Exec Time of TC'])
candidate_set_file_name = 'Candidate spec set for Regression Test'
candidate_set.to_excel(candidate_set_file_name+'.xlsx', index=False)

print(candidate_set_file_name, candidate_set_array)
print('Saving in file: ', candidate_set_file_name+'.xlsx')

result_random_output = []

def random_selection(n):
  warnings.simplefilter(action='ignore', category=FutureWarning)
  # Base case AKA Random spec selection until time ends

  random_df_spec_test_run = random_df_spec_BV_min_test_run

  random_test_case_selection = []
  item_selection = [0]*(total_number_of_specs_in_raw_data+2000)
  for index,row in random_df_spec_test_run.iterrows():
    item_selection[row['Spec ID']] = 1

  RANDOM_ALGO_EXEC_TIME = REGRESSION_TIME

  itr=0
  while True:
    if itr == NUMBER_OF_SPECS_SELECTED:
      break
    itr = itr + 1
    random_row = random_df_spec_test_run.sample(n=1)
    isCurrentExecTimeGreater = int(random_row['Total Test Exec Time']) > int(RANDOM_ALGO_EXEC_TIME)
    if isCurrentExecTimeGreater == True:
      break
    else:
      item_selection[random_row.index[0]] = 2
      RANDOM_ALGO_EXEC_TIME = RANDOM_ALGO_EXEC_TIME - int(random_row['Total Test Exec Time'])
      random_test_case_selection.append(random_row)
      random_df_spec_test_run = random_df_spec_test_run.drop(random_row.index)

  TOTAL_BV = 0
  TOTAL_TIME = 0
  for tc in random_test_case_selection:
    TOTAL_BV = TOTAL_BV + int(tc['BV'])
    TOTAL_TIME = TOTAL_TIME + int(tc['Total Test Exec Time'])


  #----- PRINT STATEMENTS -----#
  print(f'Spec BV number {n} result')
  print(f'Total BV sum in the {NUMBER_OF_SPECS_SELECTED} selected Candidate set', TOTAL_BV_IN_RANDOMLY_SELECTED_SPECS)
  print('Random TOTAL_BV SELECTED', TOTAL_BV)
  result_random_output.append(TOTAL_BV)

  print('\n')
  # print(f'Total Regression Time sum in the {NUMBER_OF_SPECS_SELECTED} selected Candidate set', TOTAL_REGRESSION_TIME_IN_RANDOMLY_SELECTED_SPECS)
  # print('REGRESSION_TIME GIVEN for running all tests', REGRESSION_TIME)
  # print('Random TOTAL_TIME TAKEN', TOTAL_TIME)
  #-----------------------------#

for i in range(10):
  random_selection(i+1)

print('Random selection output array', result_random_output)

ga_result_output = []

def ga_selection(n):

  #GA algorithm

  import random
  import warnings

  warnings.simplefilter(action='ignore', category=FutureWarning)
  max_time = REGRESSION_TIME #RTW (this overrides the global MAX_EXEC_TEST_TIME)
  pop_size = 10
  max_gen = 500
  p_crossover = 0.8
  p_mutation = 0.1

  # del sum

  def fitness_function(chromosome, candidate_set_array, max_time):
      total_value = 0
      total_time = 0
      for gene_index in range(len(chromosome)):
          if chromosome[gene_index] == 1:  # Test case is selected
              total_value += candidate_set_array[gene_index][0]  # Add business value
              total_time += candidate_set_array[gene_index][1]  # Add execution time
      if total_time > max_time:
          return 0  # Penalize solutions that exceed the max time
      return total_value

  def generate_initial_population(pop_size, chrom_length):
      population = []
      for _ in range(pop_size):
          chromosome = [random.randint(0, 1) for _ in range(chrom_length)]
          population.append(chromosome)
      return population

  def roulette_wheel_selection(population, fitnesses, num_selections):
      total_fitness = sum(fitnesses)
      selected_indices = []
      for _ in range(num_selections):
          pick = random.uniform(0, total_fitness)
          current = 0
          for i, fitness in enumerate(fitnesses):
              current += fitness
              if current > pick:
                  selected_indices.append(i)
                  break
      return [population[i] for i in selected_indices]

  def crossover(parent1, parent2):
      point = random.randint(1, len(parent1) - 1)
      child1 = parent1[:point] + parent2[point:]
      child2 = parent2[:point] + parent1[point:]
      return child1, child2

  def mutate(chromosome):
      point = random.randint(0, len(chromosome) - 1)
      chromosome[point] = 1 - chromosome[point]  # Flip the bit

  def select_best_individual(population, fitnesses):
      best_index = fitnesses.index(max(fitnesses))
      return population[best_index]

  def select_new_population(population, offspring, pop_size):
      combined = population + offspring
      combined_fitnesses = [fitness_function(ind, candidate_set_array, max_time) for ind in combined]
      sorted_indices = sorted(range(len(combined)), key=lambda k: combined_fitnesses[k], reverse=True)
      return [combined[i] for i in sorted_indices[:pop_size]]

  # Initialize population
  population = generate_initial_population(pop_size, len(candidate_set_array))

  # Evaluate initial population
  fitnesses = [fitness_function(ind, candidate_set_array, max_time) for ind in population]

  print('Initial Fitness: ', fitnesses)

  # Genetic Algorithm loop
  for generation in range(max_gen):
      # Select parents
      mating_pool = roulette_wheel_selection(population, fitnesses, pop_size)

      # Generate offspring via crossover
      offspring = []
      # print('len(mating_pool)', len(mating_pool))
      for i in range(0, pop_size, 2):
        if i >= len(mating_pool):
          break
        parent1 = mating_pool[i]
        parent2 = mating_pool[i+1]
        if random.random() < p_crossover:
            child1, child2 = crossover(parent1, parent2)
        else:
            child1, child2 = parent1, parent2
        offspring.append(child1)
        offspring.append(child2)

      # Apply mutation
      for child in offspring:
          if random.random() < p_mutation:
              mutate(child)

      # Evaluate fitness of offspring
      offspring_fitnesses = [fitness_function(ind, candidate_set_array, max_time) for ind in offspring]

      # Create new population
      population = select_new_population(population, offspring, pop_size)

      # Update fitnesses
      fitnesses = [fitness_function(ind, candidate_set_array, max_time) for ind in population]

  # Select the best solution
  best_solution = select_best_individual(population, fitnesses)
  best_fitness = fitness_function(best_solution, candidate_set_array, max_time)
  print(f'GA spec number {n} result')
  print("Best solution:", best_solution)
  print("Best fitness (total value):", best_fitness)
  ga_result_output.append(best_fitness)

  # candidate_set['GA Selection'] = best_solution
  # ga_result_file_name = 'GA Final Specs Selection Result'
  # candidate_set.to_excel(ga_result_file_name+'.xlsx', index=False)
  # print('Saving the result in file:', ga_result_file_name+'.xlsx')

for i in range(10):
  ga_selection(i+1)

print('GA selection output array', ga_result_output)