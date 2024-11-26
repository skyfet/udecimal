# udecimal.py

from decimal import Decimal, getcontext
import uuid
from weakref import WeakValueDictionary
from mpmath import mp, ln as mpmath_ln, exp as mpmath_exp, sin as mpmath_sin, cos as mpmath_cos, tan as mpmath_tan, power as mpmath_power

# Настраиваем mpmath для соответствия точности Decimal
mp.dps = 110  # количество десятичных знаков, должно быть >= getcontext().prec
getcontext().prec = 110  # Высокая точность для операций

class UDecimal:
    """
    Класс для работы с десятичными числами, содержащими неопределённость и ковариации.
    """
    # Глобальная карта для отслеживания объектов по их ID с использованием слабых ссылок
    id_map = WeakValueDictionary()
    
    def __init__(self, value, uncertainty=0):
        """
        Инициализация экземпляра UDecimal.

        :param value: Значение переменной (может быть строкой или Decimal).
        :param uncertainty: Неопределённость переменной (по умолчанию 0).
        """
        self.id = uuid.uuid4()  # Уникальный идентификатор
        self.value = Decimal(value)
        self.uncertainty = Decimal(uncertainty)
        if self.uncertainty < 0:
            raise ValueError("Неопределённость не может быть отрицательной.")
        self.contributors = {self.id}  # Множество идентификаторов вкладов
        self.covariances = {}  # Локальное хранилище ковариаций: {other_id: covariance}
        UDecimal.id_map[self.id] = self  # Добавляем в глобальную карту

    def __del__(self):
        """
        Удаление экземпляра из глобальной карты при уничтожении объекта.
        """
        if self.id in UDecimal.id_map:
            del UDecimal.id_map[self.id]

    # Методы для управления ковариациями
    def set_covariance(self, other, covariance):
        """
        Устанавливает ковариацию между текущим экземпляром и другим экземпляром.

        :param other: Экземпляр UDecimal, с которым устанавливается ковариация.
        :param covariance: Значение ковариации.
        """
        if not isinstance(other, UDecimal):
            raise TypeError("Ковариация может быть установлена только с экземпляром UDecimal.")
        self.covariances[other.id] = Decimal(covariance)
        other.covariances[self.id] = Decimal(covariance)  # Симметричное хранение

    def get_covariance(self, other):
        """
        Получает ковариацию с другим экземпляром.

        :param other: Экземпляр UDecimal, с которым запрашивается ковариация.
        :return: Значение ковариации или 0, если она не установлена.
        """
        if not isinstance(other, UDecimal):
            raise TypeError("Ковариация может быть получена только с экземпляром UDecimal.")
        return self.covariances.get(other.id, Decimal('0'))

    def remove_covariance(self, other):
        """
        Удаляет ковариацию с другим экземпляром.

        :param other: Экземпляр UDecimal, с которым удаляется ковариация.
        """
        if not isinstance(other, UDecimal):
            raise TypeError("Ковариация может быть удалена только с экземпляром UDecimal.")
        self.covariances.pop(other.id, None)
        other.covariances.pop(self.id, None)

    # Метод для объединения вкладов
    def combine_contributors(self, other):
        """
        Объединяет вкладные переменные текущего экземпляра с вкладными переменными другого экземпляра.

        :param other: Экземпляр UDecimal, чьи вкладные переменные объединяются.
        """
        self.contributors = self.contributors.union(other.contributors)

    # Арифметические операции
    def __add__(self, other):
        if isinstance(other, UDecimal):
            value = self.value + other.value
            var_x = self.uncertainty ** 2
            var_y = other.uncertainty ** 2

            # Суммируем все ковариации между вкладными переменными
            sum_covariances = Decimal('0')
            for c1 in self.contributors:
                var1 = UDecimal.id_map.get(c1)
                if var1:
                    for c2 in other.contributors:
                        var2 = UDecimal.id_map.get(c2)
                        if var2:
                            sum_covariances += var1.get_covariance(var2)
            
            variance = var_x + var_y + (2 * sum_covariances)
            uncertainty = variance.sqrt()
            result = UDecimal(value, uncertainty)

            # Объединяем вкладные переменные
            result.combine_contributors(other)
            result.combine_contributors(self)
            return result
        else:
            # Обработка сложения с числом
            value = self.value + Decimal(other)
            uncertainty = self.uncertainty
            result = UDecimal(value, uncertainty)
            result.contributors = self.contributors.copy()
            return result

    def __radd__(self, other):
        return self.__add__(other)
    
    def __sub__(self, other):
        if isinstance(other, UDecimal):
            value = self.value - other.value
            # Var(z) = Var(x) + Var(y) - 2*Cov(x,y)
            variance = (self.uncertainty ** 2) + (other.uncertainty ** 2) - (2 * self.get_covariance(other))
            uncertainty = variance.sqrt()
            result = UDecimal(value, uncertainty)
            # Объединяем вкладов
            result.combine_contributors(other)
            result.combine_contributors(self)
            return result
        else:
            value = self.value - Decimal(other)
            uncertainty = self.uncertainty
            result = UDecimal(value, uncertainty)
            result.contributors = self.contributors.copy()
            return result

    def __rsub__(self, other):
        if isinstance(other, UDecimal):
            return other.__sub__(self)
        else:
            value = Decimal(other) - self.value
            uncertainty = self.uncertainty
            result = UDecimal(value, uncertainty)
            result.contributors = self.contributors.copy()
            return result

    def __mul__(self, other):
        if isinstance(other, UDecimal):
            value = self.value * other.value
            # Относительные неопределённости
            rel_u1 = self.uncertainty / self.value
            rel_u2 = other.uncertainty / other.value
            # Ковариация относительных неопределённостей
            cov_rel = self.get_covariance(other) / (self.value * other.value)
            # Var(z) = (rel_u1)^2 + (rel_u2)^2 + 2*Cov(rel_u1, rel_u2)
            rel_variance = (rel_u1 ** 2) + (rel_u2 ** 2) + (2 * cov_rel)
            variance = rel_variance * (value ** 2)
            uncertainty = variance.sqrt()
            result = UDecimal(value, uncertainty)
            # Объединяем вкладов
            result.combine_contributors(other)
            result.combine_contributors(self)
            return result
        else:
            other = Decimal(other)
            value = self.value * other
            uncertainty = self.uncertainty * abs(other)
            result = UDecimal(value, uncertainty)
            result.contributors = self.contributors.copy()
            return result

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, UDecimal):
            value = self.value / other.value
            # Относительные неопределённости
            rel_u1 = self.uncertainty / self.value
            rel_u2 = other.uncertainty / other.value
            # Ковариация относительных неопределённостей
            cov_rel = self.get_covariance(other) / (self.value * other.value)
            # Var(z) = (rel_u1 ** 2) + (rel_u2 ** 2) - 2 * Cov(rel_u1, rel_u2)
            rel_variance = (rel_u1 ** 2) + (rel_u2 ** 2) - (2 * cov_rel)
            variance = rel_variance * (value ** 2)
            uncertainty = variance.sqrt()
            result = UDecimal(value, uncertainty)
            # Объединяем вкладов
            result.combine_contributors(other)
            result.combine_contributors(self)
            return result
        else:
            other = Decimal(other)
            value = self.value / other
            uncertainty = self.uncertainty / abs(other)
            result = UDecimal(value, uncertainty)
            result.contributors = self.contributors.copy()
            return result

    def __rtruediv__(self, other):
        # Выполняем other / self
        if isinstance(other, UDecimal):
            return other.__truediv__(self)
        else:
            other = Decimal(other)
            value = other / self.value
            # Относительные неопределённости
            rel_u1 = Decimal('0')  # other имеет нулевую неопределённость
            rel_u2 = self.uncertainty / self.value
            # Ковариация относительных неопределённостей
            # Создаём временный объект для 'other' с нулевой неопределённостью
            temp_other = UDecimal(other, Decimal('0'))
            # Устанавливаем ковариацию между temp_other и self как 0
            temp_other.set_covariance(self, Decimal('0'))
            cov_rel = temp_other.get_covariance(self) / (other * self.value)
            # Var(z) = (rel_u1 ** 2) + (rel_u2 ** 2) - 2 * Cov(rel_u1, rel_u2)
            rel_variance = (rel_u1 ** 2) + (rel_u2 ** 2) - (2 * cov_rel)
            variance = (rel_variance) * (value ** 2)
            uncertainty = variance.sqrt()
            result = UDecimal(value, uncertainty)
            result.contributors = self.contributors.copy()
            return result

    def __pow__(self, power):
        if isinstance(power, UDecimal):
            # y = x^p
            x = self.value
            p = power.value
            dx = self.uncertainty
            dp = power.uncertainty

            if x <= 0:
                raise ValueError("Основание степени должно быть положительным числом для учёта неопределённости.")

            # Используем mpmath.power для вычисления x^p
            y = Decimal(str(mpmath_power(mp.mpf(str(x)), mp.mpf(str(p)))))

            # Частные производные
            dy_dx = Decimal(str(mp.mpf(str(p)) * mpmath_power(mp.mpf(str(x)), mp.mpf(str(p - 1)))))
            dy_dp = Decimal(str(y * mpmath_ln(mp.mpf(str(x)))))

            # Ковариация между x и p
            cov_x_p = self.get_covariance(power)

            # Неопределённость
            # Var(y) = (dy_dx * dx)^2 + (dy_dp * dp)^2 + 2 * dy_dx * dy_dp * Cov(x, p)
            var_y = (dy_dx * dx) ** 2 + (dy_dp * dp) ** 2 + (2 * dy_dx * dy_dp * cov_x_p)
            delta_y = var_y.sqrt()

            result = UDecimal(y, delta_y)
            # Объединяем вкладов
            result.combine_contributors(power)
            result.combine_contributors(self)
            return result
        else:
            power = Decimal(power)
            x = self.value
            dx = self.uncertainty

            if x <= 0:
                raise ValueError("Основание степени должно быть положительным числом для учёта неопределённости.")

            # Используем mpmath.power для вычисления x^power
            y = Decimal(str(mpmath_power(mp.mpf(str(x)), mp.mpf(str(power)))))

            # Относительная неопределённость
            rel_uncertainty = abs(power) * (dx / x)
            delta_y = abs(y) * rel_uncertainty

            result = UDecimal(y, delta_y)
            result.contributors = self.contributors.copy()
            return result

    def sqrt(self):
        """
        Вычисляет квадратный корень из текущего экземпляра.

        :return: Новый экземпляр UDecimal, представляющий квадратный корень.
        """
        return self.__pow__(Decimal('0.5'))
    
    # Методы сравнения
    def __eq__(self, other):
        if isinstance(other, UDecimal):
            return (self.value == other.value) and (self.uncertainty == other.uncertainty)
        else:
            return self.value == Decimal(other)
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __lt__(self, other):
        if isinstance(other, UDecimal):
            return self.value < other.value
        else:
            return self.value < Decimal(other)
    
    def __le__(self, other):
        if isinstance(other, UDecimal):
            return self.value <= other.value
        else:
            return self.value <= Decimal(other)
    
    def __gt__(self, other):
        if isinstance(other, UDecimal):
            return self.value > other.value
        else:
            return self.value > Decimal(other)
    
    def __ge__(self, other):
        if isinstance(other, UDecimal):
            return self.value >= other.value
        else:
            return self.value >= Decimal(other)
    
    # Строковое представление
    def __str__(self):
        return f"{self.value} ± {self.uncertainty}"
    
    def __repr__(self):
        return f"UDecimal(value={self.value}, uncertainty={self.uncertainty})"
        
    # Математические функции с использованием mpmath
    def ln(self):
        """
        Вычисляет натуральный логарифм текущего экземпляра.

        :return: Новый экземпляр UDecimal, представляющий ln(x).
        """
        if self.value <= 0:
            raise ValueError("Логарифм определён только для положительных чисел.")
        # Используем mpmath для вычисления ln
        y = Decimal(str(mpmath_ln(mp.mpf(str(self.value)))))
        dy = self.uncertainty / self.value
        result = UDecimal(y, dy)
        result.contributors = self.contributors.copy()
        return result
    
    def exp(self):
        """
        Вычисляет экспоненту текущего экземпляра.

        :return: Новый экземпляр UDecimal, представляющий exp(x).
        """
        # Используем mpmath для вычисления exp
        y = Decimal(str(mpmath_exp(mp.mpf(str(self.value)))))
        dy = y * self.uncertainty
        result = UDecimal(y, dy)
        result.contributors = self.contributors.copy()
        return result
    
    def log10(self):
        """
        Вычисляет десятичный логарифм текущего экземпляра.

        :return: Новый экземпляр UDecimal, представляющий log10(x).
        """
        if self.value <= 0:
            raise ValueError("Логарифм определён только для положительных чисел.")
        # Используем mpmath для вычисления log10
        y = Decimal(str(mpmath_ln(mp.mpf(str(self.value))) / mpmath_ln(mp.mpf('10'))))
        dy = (self.uncertainty / self.value) / Decimal(str(mpmath_ln(mp.mpf('10'))))
        result = UDecimal(y, dy)
        result.contributors = self.contributors.copy()
        return result
    
    def sin(self):
        """
        Вычисляет синус текущего экземпляра (в радианах).

        :return: Новый экземпляр UDecimal, представляющий sin(x).
        """
        # Используем mpmath для вычисления sin
        value_mpf = mp.mpf(str(self.value))
        y = Decimal(str(mpmath_sin(value_mpf)))
        dy = abs(Decimal(str(mpmath_cos(value_mpf)))) * self.uncertainty
        result = UDecimal(y, dy)
        result.contributors = self.contributors.copy()
        return result
    
    def cos(self):
        """
        Вычисляет косинус текущего экземпляра (в радианах).

        :return: Новый экземпляр UDecimal, представляющий cos(x).
        """
        # Используем mpmath для вычисления cos
        value_mpf = mp.mpf(str(self.value))
        y = Decimal(str(mpmath_cos(value_mpf)))
        dy = abs(Decimal(str(mpmath_sin(value_mpf)))) * self.uncertainty
        result = UDecimal(y, dy)
        result.contributors = self.contributors.copy()
        return result
    
    def tan(self):
        """
        Вычисляет тангенс текущего экземпляра (в радианах).

        :return: Новый экземпляр UDecimal, представляющий tan(x).
        """
        # Используем mpmath для вычисления tan
        value_mpf = mp.mpf(str(self.value))
        y = Decimal(str(mpmath_tan(value_mpf)))
        cos_val = mpmath_cos(value_mpf)
        if cos_val == 0:
            raise ValueError("Тангенс не определён для данного значения.")
        dy = self.uncertainty / (Decimal(str(cos_val)) ** 2)
        result = UDecimal(y, dy)
        result.contributors = self.contributors.copy()
        return result
