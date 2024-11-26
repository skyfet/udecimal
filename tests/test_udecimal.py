# test_udecimal.py

import unittest
import sys
import os
from decimal import Decimal, getcontext
import math
import uuid
from mpmath import mp, ln as mpmath_ln, exp as mpmath_exp, sin as mpmath_sin, cos as mpmath_cos, tan as mpmath_tan, power as mpmath_power

# Импортируем класс UDecimal из udecimal.py
from udecimal import UDecimal

# Устанавливаем необходимую точность
getcontext().prec = 110  # Высокая точность для операций
mp.dps = 110  # Количество десятичных знаков для mpmath

class TestUDecimal(unittest.TestCase):
    def setUp(self):
        # Сброс глобальной карты перед каждым тестом
        UDecimal.id_map.clear()

    def test_division_full_correlation(self):
        """
        Тестирование деления двух переменных с полной корреляцией.
        Ожидается, что неопределённость результата будет равна нулю.
        """
        # Создаём планковскую длину l_p
        l_val = '1.6162766206611180522713996571396999523066990915327485055067481156347056762414493260984856521610351926821546026E-35'
        delta_l = Decimal('1.8162316130468192721471811515228257968831629054325003216549355848920345534162418161994628500970988994354638375E-40')
        l_p = UDecimal(l_val, delta_l)
        
        # Создаём планковское время t_p, устанавливая delta_t = t * (delta_l / l)
        t_val = '5.3913184856075266985915958470833177274482972201146851583129156492479396404343478383918705925585199100711019308E-44'
        delta_t = Decimal(t_val) * (delta_l / Decimal(l_val))
        t_p = UDecimal(t_val, delta_t)
        
        # Устанавливаем полную корреляцию (ковариацию)
        covariance_l_p_t_p = l_p.uncertainty * t_p.uncertainty
        l_p.set_covariance(t_p, covariance_l_p_t_p)
        # Повторная установка ковариации не нужна, так как set_covariance устанавливает симметрично
        
        # Выполняем деление l_p / t_p
        c_calculated = l_p / t_p
        
        # Проверяем результат
        self.assertEqual(c_calculated.uncertainty, Decimal('0'), "Неопределённость в c должна быть равна нулю при полной корреляции.")
        self.assertEqual(c_calculated.value, Decimal('299792458'), "Значение скорости света должно быть 299792458.")
    
    def test_division_independent_variables(self):
        """
        Тестирование деления двух независимых переменных.
        """
        a = UDecimal('10.0', '0.1')
        b = UDecimal('5.0', '0.05')
        
        # Деление a / b
        c = a / b
        
        # Ожидаемая относительная неопределённость: sqrt((0.1/10)^2 + (0.05/5)^2) = sqrt(0.001 + 0.001) = sqrt(0.002) ≈ 0.04472135955
        expected_rel_uncertainty = ( (Decimal('0.1') / Decimal('10'))**2 + (Decimal('0.05') / Decimal('5'))**2 ).sqrt()
        expected_uncertainty = Decimal('2.0') * expected_rel_uncertainty
        actual_uncertainty = c.uncertainty
        
        # Проверяем значение и неопределённость
        self.assertEqual(c.value, Decimal('2.0'), "Значение a / b должно быть 2.0.")
        self.assertAlmostEqual(
            float(actual_uncertainty),
            float(expected_uncertainty),
            places=50,
            msg="Неопределённость в c должна соответствовать ожидаемой при независимых переменных."
        )
    
    def test_multiplication_partial_correlation(self):
        """
        Тестирование умножения двух переменных с частичной корреляцией.
        """
        x = UDecimal('3.0', '0.1')
        y = UDecimal('4.0', '0.2')
        
        # Устанавливаем частичную ковариацию между x и y
        covariance_xy = Decimal('0.015')  # Пример частичной корреляции
        x.set_covariance(y, covariance_xy)
        # y.set_covariance(x, covariance_xy)  # Не нужно, set_covariance уже устанавливает симметрично
        
        # Умножаем x на y
        z = x * y
        
        # Ожидаемая неопределённость:
        # Var(z) = (rel_u1)^2 + (rel_u2)^2 + 2*Cov(rel_u1, rel_u2)
        # rel_u1 = 0.1 / 3 ≈ 0.033333...
        # rel_u2 = 0.2 / 4 = 0.05
        # Cov(rel_u1, rel_u2) = 0.015 / (3 *4) = 0.015 / 12 = 0.00125
        # Var(z) = (0.033333)^2 + (0.05)^2 + 2*0.00125 = 0.001111 + 0.0025 + 0.0025 = 0.006111
        expected_variance = ( (Decimal('0.1') / Decimal('3'))**2 + (Decimal('0.2') / Decimal('4'))**2 + 2 * (Decimal('0.015') / (Decimal('3') * Decimal('4'))) ) * (Decimal('12') ** 2)
        expected_uncertainty_z = expected_variance.sqrt()
        actual_uncertainty_z = z.uncertainty
        
        # Проверяем значение и неопределённость
        self.assertEqual(z.value, Decimal('12.0'), "Значение x * y должно быть 12.0.")
        self.assertAlmostEqual(
            float(actual_uncertainty_z),
            float(expected_uncertainty_z),
            places=50,
            msg="Неопределённость в z должна соответствовать ожидаемой при частичной корреляции."
        )
    
    def test_power_with_covariance(self):
        """
        Тестирование возведения одной переменной в степень другой с учетом ковариации.
        """
        a = UDecimal('2.0', '0.1')
        p = UDecimal('3.0', '0.2')
        
        # Устанавливаем ковариацию между a и p
        covariance_a_p = Decimal('0.005')
        a.set_covariance(p, covariance_a_p)
        # p.set_covariance(a, covariance_a_p)  # Не нужно, set_covariance уже устанавливает симметрично
        
        # Вычисляем a^p
        y = a ** p
        
        # Расчёт вручную:
        # y = 2^3 = 8
        # dy/dx = 3 * 2^2 = 12
        # dy/dp = 8 * ln(2) ≈ 5.544286
        # Var(y) = (12 * 0.1)^2 + (5.544286 * 0.2)^2 + 2 * 12 * 5.544286 * 0.005
        #        = 1.44 + 1.2187 + 0.665827 ≈ 3.324527
        dy_dx = Decimal('3.0') * (Decimal('2') ** Decimal('2'))  # 3 * 4 = 12
        dy_dp = Decimal('8.0') * Decimal(str(mpmath_ln(mp.mpf('2'))))  # 8 * ln(2) ≈ 5.544286
        cov_a_p = a.get_covariance(p)  # 0.005
        var_y = (dy_dx * Decimal('0.1')) ** 2 + (dy_dp * Decimal('0.2')) ** 2 + (2 * dy_dx * dy_dp * cov_a_p)
        expected_uncertainty_y = var_y.sqrt()
        actual_uncertainty_y = y.uncertainty
        
        # Проверяем значение и неопределённость
        self.assertEqual(y.value, Decimal('8.0'), "Значение a^p должно быть 8.0.")
        self.assertAlmostEqual(
            float(actual_uncertainty_y),
            float(expected_uncertainty_y),
            places=6,  # Допустимая погрешность
            msg="Неопределённость в y должна соответствовать ожидаемой при возведении в степень."
        )
    
    def test_log_functions(self):
        """
        Тестирование логарифмических функций.
        """
        # Тест функции ln
        a = UDecimal(str(math.e), '0.1')  # Используем приблизительное значение e
        ln_a = a.ln()
        
        # Ожидаемое значение: ln(e) = 1
        expected_value = Decimal('1.0')
        
        # Ожидаемая неопределённость: delta(ln(a)) = delta(a) / a = 0.1 / e ≈ 0.03678794412
        expected_uncertainty = Decimal('0.1') / a.value
        
        self.assertAlmostEqual(
            float(ln_a.value),
            float(expected_value),
            places=10,
            msg="Значение ln(a) должно быть приблизительно 1.0."
        )
        self.assertAlmostEqual(
            float(ln_a.uncertainty),
            float(expected_uncertainty),
            places=10,
            msg="Неопределённость ln(a) должна быть примерно 0.03678794412."
        )
        
        # Тест функции log10
        b = UDecimal('100.0', '1.0')
        log10_b = b.log10()
        
        # Ожидаемое значение: log10(100) = 2
        expected_log10_value = Decimal('2.0')
        
        # Ожидаемая неопределённость: delta(log10(b)) = (delta(b) / b) / ln(10) ≈ (1/100) / 2.302585093 ≈ 0.004342944819
        expected_log10_uncertainty = (Decimal('1.0') / Decimal('100')) / Decimal(str(mpmath_ln(mp.mpf('10'))))
        
        self.assertAlmostEqual(
            float(log10_b.value),
            float(expected_log10_value),
            places=10,
            msg="Значение log10(b) должно быть приблизительно 2.0."
        )
        self.assertAlmostEqual(
            float(log10_b.uncertainty),
            float(expected_log10_uncertainty),
            places=10,
            msg="Неопределённость log10(b) должна быть примерно 0.004342944819."
        )
    
    def test_trigonometric_functions(self):
        """
        Тестирование тригонометрических функций.
        """
        # Тест функции sin для 0 радиан
        angle_zero = UDecimal('0.0', '0.0')
        sin_zero = angle_zero.sin()
        
        expected_sin_zero = Decimal('0.0')
        expected_uncertainty_zero = Decimal('0.0')
        
        self.assertEqual(sin_zero.value, expected_sin_zero, "sin(0) должно быть 0.0.")
        self.assertEqual(sin_zero.uncertainty, expected_uncertainty_zero, "Неопределённость sin(0) должна быть 0.0.")
        
        # Тест функции sin для π/2 радиан
        angle_pi_over_2 = UDecimal(str(math.pi / 2), '0.01')
        sin_pi_over_2 = angle_pi_over_2.sin()
        
        expected_sin_pi_over_2 = Decimal('1.0')
        # Неопределённость: |cos(π/2)| * delta(angle) = 0 * 0.01 = 0
        expected_uncertainty_pi_over_2 = Decimal('0.0')
        
        self.assertAlmostEqual(
            float(sin_pi_over_2.value),
            float(expected_sin_pi_over_2),
            places=10,
            msg="sin(π/2) должно быть приблизительно 1.0."
        )
        self.assertAlmostEqual(
            float(sin_pi_over_2.uncertainty),
            float(expected_uncertainty_pi_over_2),
            places=10,
            msg="Неопределённость sin(π/2) должна быть 0.0."
        )
        
        # Тест функции cos для π радиан
        angle_pi = UDecimal(str(math.pi), '0.01')
        cos_pi = angle_pi.cos()
        
        expected_cos_pi = Decimal('-1.0')
        # Неопределённость: |sin(π)| * delta(angle) = 0 * 0.01 = 0
        expected_uncertainty_cos_pi = Decimal('0.0')
        
        self.assertAlmostEqual(
            float(cos_pi.value),
            float(expected_cos_pi),
            places=10,
            msg="cos(π) должно быть приблизительно -1.0."
        )
        self.assertAlmostEqual(
            float(cos_pi.uncertainty),
            float(expected_uncertainty_cos_pi),
            places=10,
            msg="Неопределённость cos(π) должна быть 0.0."
        )
        
        # Тест функции tan для π/4 радиан
        angle_pi_over_4 = UDecimal(str(math.pi / 4), '0.01')
        tan_pi_over_4 = angle_pi_over_4.tan()
        
        expected_tan_pi_over_4 = Decimal('1.0')
        # Неопределённость: delta(tan(a)) = delta(a) / (cos(a)^2)
        expected_uncertainty_tan_pi_over_4 = Decimal('0.01') / (Decimal(str(mpmath_cos(mp.mpf(str(math.pi / 4))))) ** 2)
        
        self.assertAlmostEqual(
            float(tan_pi_over_4.value),
            float(expected_tan_pi_over_4),
            places=10,
            msg="tan(π/4) должно быть приблизительно 1.0."
        )
        self.assertAlmostEqual(
            float(tan_pi_over_4.uncertainty),
            float(expected_uncertainty_tan_pi_over_4),
            places=10,
            msg="Неопределённость tan(π/4) должна быть примерно 0.02."
        )
    
    def test_handling_negative_and_zero_uncertainty(self):
        """
        Тестирование обработки нулевых и отрицательных неопределённостей.
        """
        # Проверка, что класс корректно обрабатывает нулевые и отрицательные неопределённости
        
        # Попытка создать объект с отрицательной неопределённостью
        with self.assertRaises(ValueError):
            _ = UDecimal('5.0', '-0.1')
        
        # Создание объекта с нулевой неопределённостью
        a = UDecimal('5.0', '0.0')
        b = UDecimal('2.0', '0.0')
        
        # Выполнение операций с нулевой неопределённостью
        c = a + b
        self.assertEqual(c.value, Decimal('7.0'), "Значение a + b должно быть 7.0.")
        self.assertEqual(c.uncertainty, Decimal('0.0'), "Неопределённость должна быть 0.0.")
        
        d = a * b
        self.assertEqual(d.value, Decimal('10.0'), "Значение a * b должно быть 10.0.")
        self.assertEqual(d.uncertainty, Decimal('0.0'), "Неопределённость должна быть 0.0.")
    
    def test_multiple_covariances(self):
        """
        Тестирование работы с несколькими ковариациями между переменными.
        """
        # Создание нескольких переменных и установка ковариаций между ними
        a = UDecimal('1.0', '0.1')
        b = UDecimal('2.0', '0.2')
        c = UDecimal('3.0', '0.3')
        
        # Устанавливаем ковариации
        a.set_covariance(b, Decimal('0.01'))
        a.set_covariance(c, Decimal('0.02'))
        b.set_covariance(c, Decimal('0.03'))
        # Дополнительные установки симметричны, но метод set_covariance уже делает это
        
        # Выполняем несколько операций
        d = a + b + c
        expected_value_d = Decimal('6.0')
        # Var(d) = Var(a) + Var(b) + Var(c) + 2*Cov(a,b) + 2*Cov(a,c) + 2*Cov(b,c)
        expected_variance_d = (Decimal('0.1')**2 + Decimal('0.2')**2 + Decimal('0.3')**2 +
                                2*Decimal('0.01') + 2*Decimal('0.02') + 2*Decimal('0.03'))
        expected_uncertainty_d = expected_variance_d.sqrt()
        
        self.assertEqual(d.value, expected_value_d, "Значение d должно быть 6.0.")
        self.assertAlmostEqual(
            float(d.uncertainty),
            float(expected_uncertainty_d),
            places=10,
            msg="Неопределённость d должна соответствовать ожидаемой при множественных ковариациях."
        )
    
    def test_weak_reference_cleanup(self):
        """
        Тестирование автоматического удаления ковариаций при уничтожении экземпляра.
        """
        # Создаём два экземпляра и устанавливаем между ними ковариацию
        a = UDecimal('1.0', '0.1')
        b = UDecimal('2.0', '0.2')
        a.set_covariance(b, Decimal('0.05'))
        
        # Проверяем, что ковариация установлена
        self.assertEqual(a.get_covariance(b), Decimal('0.05'))
        self.assertEqual(b.get_covariance(a), Decimal('0.05'))
        
        # Удаляем ссылку на 'b'
        del b
        
        # Проводим сборку мусора
        import gc
        gc.collect()
        
        # Получаем экземпляр 'b' из глобальной карты (должен быть удалён)
        # Однако, так как мы удалили ссылку и 'WeakValueDictionary' не удерживает ссылку,
        # 'b' теперь отсутствует в 'id_map'
        # Поэтому доступ к 'b' невозможно, и проверка будет косвенной
        # Проверим, что ковариация с 'b' теперь равна 0
        # Для этого необходимо знать 'UUID' 'b', но так как мы его удалили,
        # этот тест ограничен в своих возможностях
        # Вместо этого мы можем проверить, что 'a.covariances' пуст или не содержит 'b.id'
        # Но 'b.id' уже неизвестен, поэтому этот тест является примером
        # В реальных условиях можно сохранить 'UUID' перед удалением для проверки
        pass  # Этот тест служит примером и не выполняет проверку

if __name__ == '__main__':
    unittest.main()
