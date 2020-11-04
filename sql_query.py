from mysql.connector.pooling import MySQLConnectionPool
from decouple import config

connection = {'host': config('CLEAR_DB_HOST'),
	'user': config('CLEAR_DB_USER'),
	'password': config('CLEAR_DB_PASSWORD'),
	'database': config('CLEAR_DB_DATABASE')
}
pool = MySQLConnectionPool(pool_name='primary_pool', **connection)

class SQLQuery():
	def __init__(self):
		self.pool = pool
		
	def raw_query(self, query):
		try:
			con = self.pool.get_connection()
			cursor = con.cursor()
			
			print(query)
			cursor.execute(query)
			
			result = cursor.fetchall()
			cursor.close()
			con.commit()
			con.close()
			return result
			
		except Exception as e:
			print(e)
			cursor.close()
			con.close()
			raise Exception

	def insert_and_update(self, target_table, columns, row, key_list):
		try:
			con = self.pool.get_connection()
			cursor = con.cursor()

			data_str = str(tuple(row))[:-2] + str(tuple(row))[-2:].replace(',', '')
			update_cols = columns.copy()
			update_cols = [col for col in update_cols if col not in key_list]
			update_vals = [f'{col}=VALUES({col})' for col in update_cols]
			
			query_string = 'INSERT INTO %s (%s) VALUES %s' %(target_table, ', '.join(columns), data_str)
			if update_vals:
				query_string += ' ON DUPLICATE KEY UPDATE %s' %(', '.join(update_vals))
			print(query_string)
			cursor.execute(query_string)

			cursor.close()
			con.commit()
			con.close()

		except Exception as e:
			print(e)
			cursor.close()
			con.close()
			raise Exception
	
	def update_by_increment(self, target_table, columns, key_list, key_values, increment=1):
		try:
			con = self.pool.get_connection()
			cursor = con.cursor()

			update_cols = [f'{col} = {col} + {increment}' for col in columns]
			key_values_tuples = [str(tuple(keys)) if len(keys) > 1 else str(tuple(keys)).replace(',','') for keys in key_values]
			key_values_joined = ['%s IN %s' %(key_list[i], key_values_tuples[i]) for i in range(len(key_list))]
			
			query_string = 'UPDATE %s SET %s WHERE %s' %(target_table, ', '.join(update_cols), ' AND '.join(key_values_joined))
			print(query_string)
			cursor.execute(query_string)

			cursor.close()
			con.commit()
			con.close()

		except Exception as e:
			print(e)
			cursor.close()
			con.close()
			raise Exception

	def delete_data(self, target_table, key_list, key_values):
		try:
			con = self.pool.get_connection()
			cursor = con.cursor()

			key_values_tuples = [str(tuple(keys)) if len(keys) > 1 else str(tuple(keys)).replace(',','') for keys in key_values]
			key_values_joined = ['%s IN %s' %(key_list[i], key_values_tuples[i]) for i in range(len(key_list))]
			
			query_string = 'DELETE FROM %s WHERE %s' %(target_table, ' AND '.join(key_values_joined))
			print(query_string)
			cursor.execute(query_string)
			
			cursor.close()
			con.commit()
			con.close()

		except Exception as e:
			print(e)
			cursor.close()
			con.close()
			raise Exception

	def select_data(self, table, columns, **kwargs):
		try:
			con = self.pool.get_connection()
			cursor = con.cursor()

			col_query = ', '.join(columns)
			deep_query_string = ''

			if kwargs:
				if 'condition' in list(kwargs.keys()):
					arg = 'condition'
					var_params = []
					for i in range(len(kwargs[arg][0])):
						vals = kwargs[arg][i+1]
						vals = str(tuple(vals))[:-2] + str(tuple(vals))[-2:].replace(',', '')
						var_params.append(f'{kwargs[arg][0][i]} IN {vals}')
					deep_query_string += ' WHERE %s' %(' AND '.join(var_params))

			base_query_string = 'SELECT %s FROM %s' %(col_query, table,)
			final_query = base_query_string + deep_query_string
			print(final_query)
			cursor.execute(final_query)
			
			result = cursor.fetchall()
			cursor.close()
			con.close()
			return result

		except Exception as e:
			print(e)
			cursor.close()
			con.close()
			raise Exception