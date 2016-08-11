# coding=utf-8
import psycopg2
import config
import xlrd


class RatingDao:
    def __init__(self):
        self.__connection = psycopg2.connect(database=config.db,
                                             user=config.usr,
                                             password=config.pw,
                                             host=config.host,
                                             port=config.port)

    def select_query(self, query):
        cur = self.__connection.cursor()
        cur.execute(query)
        return cur.fetchall()

    def update_query(self, query):
        cur = self.__connection.cursor()
        cur.execute(query)
        self.__connection.commit()

    def close_connection(self):
        self.__connection.close()

    def check_user(self, telegram_id):
        return len(self.select_query('SELECT * FROM USER_ WHERE telegram_id = ' + str(telegram_id))) > 0

    def get_benefit(self, telegram_id):
        rows = self.select_query('SELECT benefit FROM USER_ WHERE telegram_id = ' + str(telegram_id))
        if len(rows) != 0:
            return rows[0][0]
        else:
            return 'Информация об улучшениях отсутствует.'

    def get_rating(self, telegram_id):
        rows = self.select_query('SELECT rating, rating_comment FROM USER_ WHERE telegram_id = ' + str(telegram_id))
        if len(rows) != 0:
            return rows
        else:
            return False

    def get_problems(self, telegram_id):
        return self.select_query('SELECT description FROM problem ' +
                                 'INNER JOIN user_ ON problem.user_id = user_.id ' +
                                 'WHERE user_.telegram_id = ' + str(telegram_id))

    def get_action(self, telegram_id):
        action = self.get_next_action_desc(telegram_id)
        if len(action) == 0:
            self.update_query('UPDATE action SET IS_ACTIVE = NULL')
            action = self.get_next_action_desc(telegram_id)
            if len(action) == 0:
                return False
        action_id = action[0][0]
        self.update_query('UPDATE action SET IS_ACTIVE = TRUE WHERE id = ' + str(action_id))
        return action[0][1]

    def get_next_action_desc(self, telegram_id):
        return self.select_query('SELECT a.id, a.action_desc FROM action a ' +
                                 'INNER JOIN user_ ON a.user_id = user_.id ' +
                                 'WHERE a.is_done ISNULL ' +
                                 'AND a.is_active ISNULL ' +
                                 'AND user_.telegram_id = ' + str(telegram_id) +
                                 ' ORDER BY a.id ASC LIMIT 1')

    def set_action_done(self, telegram_id, is_success):
        action = self.get_active_action(telegram_id)
        if len(action) != 0:
            self.update_query('UPDATE action SET IS_DONE = ' + str(is_success) + ' WHERE id = ' + str(action[0][0]))

    def log_action_comment(self, telegram_id, comment):
        action = self.get_last_action(telegram_id)
        if len(action) != 0:
            self.update_query(
                "UPDATE action SET action_comment = '" + str(comment) + "' WHERE id = " + str(action[0][0]))
            return True
        else:
            return False

    def get_active_action(self, telegram_id):
        return self.select_query('SELECT a.id, a.action_desc FROM action a ' +
                                 'INNER JOIN user_ ON a.user_id = user_.id ' +
                                 'WHERE a.is_done ISNULL ' +
                                 'AND a.is_active = TRUE ' +
                                 'AND user_.telegram_id = ' + str(telegram_id) +
                                 ' ORDER BY a.id DESC LIMIT 1')

    def get_last_action(self, telegram_id):
        return self.select_query("SELECT a.id, a.action_desc FROM action a " +
                                 "INNER JOIN user_ ON a.user_id = user_.id " +
                                 "WHERE a.is_done = FALSE " +
                                 "AND a.is_active = TRUE " +
                                 "AND a.action_comment = '' " +
                                 "AND user_.telegram_id = " + str(telegram_id) +
                                 " ORDER BY a.id DESC LIMIT 1")

    def insert_db_info(self, document):
        rb = xlrd.open_workbook(file_contents=document)
        self.truncate_db()
        sheet = rb.sheet_by_index(0)
        for rownum in range(sheet.nrows):
            if rownum == 0:
                continue
            row = sheet.row_values(rownum)
            self.insert_user_info(row[0], row[1], row[2], row[3], row[11])
            for x in range(4, 7):
                self.insert_problems(row[x], row[0])
            for x in range(7, 11):
                self.insert_actions(row[x], row[0])

    def insert_user_info(self, telegram_id, phone, rating, rating_comment, benefit):
        cur = self.__connection.cursor()
        query = "INSERT INTO USER_ VALUES (nextval('user__id_seq'), " \
                "{0}, '{1}', {2}, '{3}', '{4}')".format(telegram_id,
                                                        phone,
                                                        rating,
                                                        rating_comment,
                                                        benefit)
        cur.execute(query)
        self.__connection.commit()

    def insert_problems(self, problem_desc, telegram_id):
        if problem_desc:
            cur = self.__connection.cursor()
            query = "INSERT INTO PROBLEM VALUES (nextval('problem_id_seq'), '{0}', {1})".format(problem_desc,
                                                                                                telegram_id)
            cur.execute(query)
            self.__connection.commit()

    def insert_actions(self, action_desc, telegram_id):
        if action_desc:
            cur = self.__connection.cursor()
            query = "INSERT INTO ACTION VALUES (nextval('action_id_seq'), '{0}', '', {1}, NULL)".format(action_desc,
                                                                                                        telegram_id)
            cur.execute(query)
            self.__connection.commit()

    def truncate_db(self):
        cur = self.__connection.cursor()
        problem = 'TRUNCATE PROBLEM CASCADE'
        action = 'TRUNCATE ACTION CASCADE'
        user = 'TRUNCATE USER_ CASCADE'
        cur.execute(problem)
        cur.execute(action)
        cur.execute(user)
        self.__connection.commit()
