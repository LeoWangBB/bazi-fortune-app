"""
八字算命应用后端
包含完整的八字排盘算法和命理分析
"""

import os
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from zhdate import ZhDate
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from dateutil import parser as date_parser
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# ============== 常量定义 ==============

# 天干
HEAVENLY_STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
# 地支
EARTHLY_BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 五行
FIVE_ELEMENTS = ['木', '火', '土', '金', '水']

# 五行对应关系
STEM_ELEMENT = {
    '甲': '木', '乙': '木',
    '丙': '火', '丁': '火',
    '戊': '土', '己': '土',
    '庚': '金', '辛': '金',
    '壬': '水', '癸': '水'
}

BRANCH_ELEMENT = {
    '子': '水', '丑': '土', '寅': '木', '卯': '木',
    '辰': '土', '巳': '火', '午': '火', '未': '土',
    '申': '金', '酉': '金', '戌': '土', '亥': '水'
}

# 地支藏干
BRANCH_HIDDEN_STEMS = {
    '子': ['癸'],
    '丑': ['癸', '辛', '己'],
    '寅': ['甲', '丙', '戊'],
    '卯': ['乙'],
    '辰': ['乙', '戊', '癸'],
    '巳': ['丙', '庚', '戊'],
    '午': ['丁', '己'],
    '未': ['丁', '乙', '己'],
    '申': ['庚', '壬', '戊'],
    '酉': ['辛'],
    '戌': ['辛', '丁', '戊'],
    '亥': ['壬', '甲']
}

# 十神计算（以日干为基准）
TEN_GODS = {
    '甲': {'甲': '比肩', '乙': '劫财', '丙': '食神', '丁': '伤官', '戊': '偏财', '己': '正财', '庚': '七杀', '辛': '正官', '壬': '偏印', '癸': '正印'},
    '乙': {'甲': '劫财', '乙': '比肩', '丙': '伤官', '丁': '食神', '戊': '正财', '己': '偏财', '庚': '正官', '辛': '七杀', '壬': '正印', '癸': '偏印'},
    '丙': {'甲': '偏印', '乙': '正印', '丙': '比肩', '丁': '劫财', '戊': '食神', '己': '伤官', '庚': '偏财', '辛': '正财', '壬': '七杀', '癸': '正官'},
    '丁': {'甲': '正印', '乙': '偏印', '丙': '劫财', '丁': '比肩', '戊': '伤官', '己': '食神', '庚': '正财', '辛': '偏财', '壬': '正官', '癸': '七杀'},
    '戊': {'甲': '七杀', '乙': '正官', '丙': '偏印', '丁': '正印', '戊': '比肩', '己': '劫财', '庚': '食神', '辛': '伤官', '壬': '偏财', '癸': '正财'},
    '己': {'甲': '正官', '乙': '七杀', '丙': '正印', '丁': '偏印', '戊': '劫财', '己': '比肩', '庚': '伤官', '辛': '食神', '壬': '正财', '癸': '偏财'},
    '庚': {'甲': '偏财', '乙': '正财', '丙': '七杀', '丁': '正官', '戊': '偏印', '己': '正印', '庚': '比肩', '辛': '劫财', '壬': '食神', '癸': '伤官'},
    '辛': {'甲': '正财', '乙': '偏财', '丙': '正官', '丁': '七杀', '戊': '正印', '己': '偏印', '庚': '劫财', '辛': '比肩', '壬': '伤官', '癸': '食神'},
    '壬': {'甲': '食神', '乙': '伤官', '丙': '偏财', '丁': '正财', '戊': '七杀', '己': '正官', '庚': '偏印', '辛': '正印', '壬': '比肩', '癸': '劫财'},
    '癸': {'甲': '伤官', '乙': '食神', '丙': '正财', '丁': '偏财', '戊': '正官', '己': '七杀', '庚': '正印', '辛': '偏印', '壬': '劫财', '癸': '比肩'}
}

# 五行相生相克
ELEMENT_GENERATE = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
ELEMENT_OVERCOME = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}

# 月支对应的天干（年干决定月干）
MONTH_STEM_TABLE = {
    '子': '甲', '丑': '乙', '寅': '丙', '卯': '丁', '辰': '戊', '巳': '己',
    '午': '庚', '未': '辛', '申': '壬', '酉': '癸', '戌': '甲', '亥': '乙'
}

# 时支对应的天干（日干决定时干）
HOUR_STEM_CYCLE = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']

# 神煞
SHEN_SHA = {
    '天乙贵人': ['甲', '戊', '庚'],
    '太极贵人': ['壬', '癸', '甲', '乙', '丙', '丁', '戊', '己'],
    '驿马': ['申', '巳', '亥', '寅'],
    '桃花': ['申', '子', '辰', '酉'],
}

# ============== 农历转换类 ==============

class LunarCalendar:
    """公历农历转换类"""

    # 农历月份天数
    LUNAR_MONTH_DAYS = [29, 30]
    # 农历年份天数（大致）
    LUNAR_YEAR_DAYS = [354, 383]

    # 1900-2100年农历数据（简化版）
    LUNAR_DATA = {
        1900: (0, 13, 4716, 0),  # 庚子年
        1901: (0, 1, 4894, 0),
        1902: (0, 2, 5016, 0),
        1903: (0, 3, 5150, 0),
        1904: (0, 4, 5284, 0),
        1905: (0, 5, 5418, 0),
        1906: (0, 6, 5552, 0),
        1907: (0, 0, 5686, 0),
        1908: (0, 1, 5820, 0),
        1909: (0, 2, 5954, 0),
        1910: (0, 3, 6088, 0),
        1911: (0, 4, 6222, 0),
        1912: (0, 5, 6356, 0),
        1913: (0, 6, 6490, 0),
        1914: (0, 0, 6624, 0),
        1915: (0, 1, 6758, 0),
        1916: (0, 2, 6892, 0),
        1917: (0, 3, 7026, 0),
        1918: (0, 4, 7160, 0),
        1919: (0, 5, 7294, 0),
        1920: (0, 6, 7428, 0),
        1921: (0, 0, 7562, 0),
        1922: (0, 1, 7696, 0),
        1923: (0, 2, 7830, 0),
        1924: (0, 3, 7964, 0),
        1925: (0, 4, 8098, 0),
        1926: (0, 5, 8232, 0),
        1927: (0, 6, 8366, 0),
        1928: (0, 0, 8500, 0),
        1929: (0, 1, 8634, 0),
        1930: (0, 2, 8768, 0),
        1931: (0, 3, 8902, 0),
        1932: (0, 4, 9036, 0),
        1933: (0, 5, 9170, 0),
        1934: (0, 6, 9304, 0),
        1935: (0, 0, 9438, 0),
        1936: (0, 1, 9572, 0),
        1937: (0, 2, 9706, 0),
        1938: (0, 3, 9840, 0),
        1939: (0, 4, 9974, 0),
        1940: (0, 5, 10108, 0),
        1941: (0, 6, 10242, 0),
        1942: (0, 0, 10376, 0),
        1943: (0, 1, 10510, 0),
        1944: (0, 2, 10644, 0),
        1945: (0, 3, 10778, 0),
        1946: (0, 4, 10912, 0),
        1947: (0, 5, 11046, 0),
        1948: (0, 6, 11180, 0),
        1949: (0, 0, 11314, 0),
        1950: (0, 1, 11448, 0),
        1951: (0, 2, 11582, 0),
        1952: (0, 3, 11716, 0),
        1953: (0, 4, 11850, 0),
        1954: (0, 5, 11984, 0),
        1955: (0, 6, 12118, 0),
        1956: (0, 0, 12252, 0),
        1957: (0, 1, 12386, 0),
        1958: (0, 2, 12520, 0),
        1959: (0, 3, 12654, 0),
        1960: (0, 4, 12788, 0),
        1961: (0, 5, 12922, 0),
        1962: (0, 6, 13056, 0),
        1963: (0, 0, 13190, 0),
        1964: (0, 1, 13324, 0),
        1965: (0, 2, 13458, 0),
        1966: (0, 3, 13592, 0),
        1967: (0, 4, 13726, 0),
        1968: (0, 5, 13860, 0),
        1969: (0, 6, 13994, 0),
        1970: (0, 0, 14128, 0),
        1971: (0, 1, 14262, 0),
        1972: (0, 2, 14396, 0),
        1973: (0, 3, 14530, 0),
        1974: (0, 4, 14664, 0),
        1975: (0, 5, 14798, 0),
        1976: (0, 6, 14932, 0),
        1977: (0, 0, 15066, 0),
        1978: (0, 1, 15200, 0),
        1979: (0, 2, 15334, 0),
        1980: (0, 3, 15468, 0),
        1981: (0, 4, 15602, 0),
        1982: (0, 5, 15736, 0),
        1983: (0, 6, 15870, 0),
        1984: (0, 0, 16004, 0),
        1985: (0, 1, 16138, 0),
        1986: (0, 2, 16272, 0),
        1987: (0, 3, 16406, 0),
        1988: (0, 4, 16540, 0),
        1989: (0, 5, 16674, 0),
        1990: (0, 6, 16808, 0),
        1991: (0, 0, 16942, 0),
        1992: (0, 1, 17076, 0),
        1993: (0, 2, 17210, 0),
        1994: (0, 3, 17344, 0),
        1995: (0, 4, 17478, 0),
        1996: (0, 5, 17612, 0),
        1997: (0, 6, 17746, 0),
        1998: (0, 0, 17880, 0),
        1999: (0, 1, 18014, 0),
        2000: (0, 2, 18148, 0),
        2001: (0, 3, 18282, 0),
        2002: (0, 4, 18416, 0),
        2003: (0, 5, 18550, 0),
        2004: (0, 6, 18684, 0),
        2005: (0, 0, 18818, 0),
        2006: (0, 1, 18952, 0),
        2007: (0, 2, 19086, 0),
        2008: (0, 3, 19220, 0),
        2009: (0, 4, 19354, 0),
        2010: (0, 5, 19488, 0),
        2011: (0, 6, 19622, 0),
        2012: (0, 0, 19756, 0),
        2013: (0, 1, 19890, 0),
        2014: (0, 2, 20024, 0),
        2015: (0, 3, 20158, 0),
        2016: (0, 4, 20292, 0),
        2017: (0, 5, 20426, 0),
        2018: (0, 6, 20560, 0),
        2019: (0, 0, 20694, 0),
        2020: (0, 1, 20828, 0),
        2021: (0, 2, 20962, 0),
        2022: (0, 3, 21096, 0),
        2023: (0, 4, 21230, 0),
        2024: (0, 5, 21364, 0),
        2025: (0, 6, 21498, 0),
        2026: (0, 0, 21632, 0),
    }

    # 农历月份名称
    LUNAR_MONTH_NAMES = ['', '正月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '冬月', '腊月']
    # 农历日期名称
    LUNAR_DAY_NAMES = ['初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
                       '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
                       '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十']

    # 天干地支年号
    TIANGAN_NAMES = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    DIZHI_NAMES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

    @staticmethod
    def solar_to_lunar(year: int, month: int, day: int) -> tuple:
        """公历转农历（使用zhdate库确保准确性）"""
        try:
            dt = datetime(year, month, day)
            lunar = ZhDate.from_datetime(dt)
            return (lunar.lunar_year, lunar.lunar_month, lunar.lunar_day)
        except Exception:
            # Fallback to simplified algorithm
            base_date = datetime(1900, 1, 31)
            target_date = datetime(year, month, day)
            days = (target_date - base_date).days

            lunar_year = 1900
            while True:
                year_days = LunarCalendar._get_lunar_year_days(lunar_year)
                if days < year_days:
                    break
                days -= year_days
                lunar_year += 1

            month_days = [29, 30]
            lunar_month = 1

            while True:
                if days < month_days[0]:
                    break
                days -= month_days[0]
                lunar_month += 1

            lunar_day = days + 1
            return (lunar_year, lunar_month, lunar_day)

    @staticmethod
    def _get_lunar_year_days(year: int) -> int:
        """获取农历年天数"""
        if year in LunarCalendar.LUNAR_DATA:
            # 简化：每一年大致354天
            return 354
        return 354

    @staticmethod
    def get_ganzhi_year(year: int) -> str:
        """获取天干地支年"""
        stem_index = (year - 4) % 10
        branch_index = (year - 4) % 12
        return LunarCalendar.TIANGAN_NAMES[stem_index] + LunarCalendar.DIZHI_NAMES[branch_index]

    @staticmethod
    def get_ganzhi_month(year_gan: str, month: int) -> str:
        """获取天干地支月"""
        month_gan_index = (HEAVENLY_STEMS.index(year_gan) * 2 + month) % 10
        return HEAVENLY_STEMS[month_gan_index] + EARTHLY_BRANCHES[month % 12]

    @staticmethod
    def get_ganzhi_day(year: int, month: int, day: int) -> str:
        """获取天干地支日（简化算法）"""
        # 1898年1月1日是甲子日
        base_date = datetime(1898, 1, 1)
        target_date = datetime(year, month, day)
        days = (target_date - base_date).days

        stem_index = days % 10
        branch_index = days % 12
        return HEAVENLY_STEMS[stem_index] + EARTHLY_BRANCHES[branch_index]

    @staticmethod
    def get_ganzhi_hour(ganzhi_day: str, hour: int) -> str:
        """获取天干地支时"""
        # 子时(23:00-1:00)开始
        branch_index = (hour + 1) // 2 % 12

        # 日干决定时干
        day_gan_index = HEAVENLY_STEMS.index(ganzhi_day[0])
        hour_gan_index = (day_gan_index * 2 + branch_index) % 10

        return HEAVENLY_STEMS[hour_gan_index] + EARTHLY_BRANCHES[branch_index]


# ============== 八字排盘类 ==============

class BaziCalculator:
    """八字排盘计算类"""

    def __init__(self, year: int, month: int, day: int, hour: int, minute: int, birthplace: str = ""):
        self.birth_date = datetime(year, month, day, hour, minute)
        self.birthplace = birthplace
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute

    def calculate(self) -> Dict[str, Any]:
        """计算完整八字（自动将公历转换为农历）"""
        # 自动将公历转换为农历
        lunar_date = LunarCalendar.solar_to_lunar(self.year, self.month, self.day)
        lunar_year, lunar_month, lunar_day = lunar_date[0], lunar_date[1], lunar_date[2]

        # 使用农历年份计算年柱
        year_ganzhi = LunarCalendar.get_ganzhi_year(lunar_year)
        year_stem = year_ganzhi[0]
        year_branch = year_ganzhi[1]

        # 使用农历月份计算月柱
        month_ganzhi = LunarCalendar.get_ganzhi_month(year_stem, lunar_month)
        month_stem = month_ganzhi[0]
        month_branch = month_ganzhi[1]

        # 日柱必须使用公历日期计算（基于1900年1月1日是甲子日）
        day_ganzhi = LunarCalendar.get_ganzhi_day(self.year, self.month, self.day)
        day_stem = day_ganzhi[0]
        day_branch = day_ganzhi[1]

        # 时柱
        hour_ganzhi = LunarCalendar.get_ganzhi_hour(day_ganzhi, self.hour)
        hour_stem = hour_ganzhi[0]
        hour_branch = hour_ganzhi[1]

        return {
            'year': {'stem': year_stem, 'branch': year_branch, 'ganzhi': year_ganzhi},
            'month': {'stem': month_stem, 'branch': month_branch, 'ganzhi': month_ganzhi},
            'day': {'stem': day_stem, 'branch': day_branch, 'ganzhi': day_ganzhi},
            'hour': {'stem': hour_stem, 'branch': hour_branch, 'ganzhi': hour_ganzhi},
            'birth_date': self.birth_date.strftime('%Y-%m-%d %H:%M'),
            'birthplace': self.birthplace,
            'lunar_date': f"{lunar_year}年{lunar_month}月{lunar_day}日"
        }

    def get_day_master(self) -> str:
        """获取日主"""
        bazi = self.calculate()
        return bazi['day']['stem']

    def get_element_balance(self) -> Dict[str, int]:
        """计算五行平衡"""
        bazi = self.calculate()
        elements = {
            '木': 0, '火': 0, '土': 0, '金': 0, '水': 0
        }

        for pillar in ['year', 'month', 'day', 'hour']:
            stem = bazi[pillar]['stem']
            branch = bazi[pillar]['branch']

            # 天干五行
            if stem in STEM_ELEMENT:
                elements[STEM_ELEMENT[stem]] += 1

            # 地支五行
            if branch in BRANCH_ELEMENT:
                elements[BRANCH_ELEMENT[branch]] += 1

            # 地支藏干
            if branch in BRANCH_HIDDEN_STEMS:
                for hs in BRANCH_HIDDEN_STEMS[branch]:
                    if hs in STEM_ELEMENT:
                        elements[STEM_ELEMENT[hs]] += 0.5

        return elements

    def get_ten_gods(self) -> Dict[str, str]:
        """计算十神"""
        bazi = self.calculate()
        day_stem = bazi['day']['stem']

        ten_gods = {}
        for pillar in ['year', 'month', 'day', 'hour']:
            stem = bazi[pillar]['stem']
            ten_gods[pillar] = TEN_GODS[day_stem].get(stem, '')

        return ten_gods

    def get_xingxiang(self) -> str:
        """获取命局（身强身弱）"""
        elements = self.get_element_balance()
        day_master = self.get_day_master()

        # 日主五行
        day_element = STEM_ELEMENT.get(day_master, '')

        # 计算日主力量
        day_power = elements.get(day_element, 0)

        # 计算克制日主和生扶日主的力量
        if day_element in ELEMENT_OVERCOME:
            conqueror = ELEMENT_OVERCOME[day_element]
            conquer_power = elements.get(conqueror, 0)
        else:
            conquer_power = 0

        if day_element in ELEMENT_GENERATE:
            supporter = ELEMENT_GENERATE[day_element]
            support_power = elements.get(supporter, 0)
        else:
            support_power = 0

        # 简单判断
        if support_power > conquer_power + 2:
            return '身强'
        elif conquer_power > support_power + 2:
            return '身弱'
        else:
            return '身中'


# ============== 命理分析类 ==============

class BaziAnalyzer:
    """命理分析类"""

    def __init__(self, bazi_data: Dict[str, Any]):
        self.bazi = bazi_data
        self.calculator = BaziCalculator(
            self.bazi['birth_date'].year,
            self.bazi['birth_date'].month,
            self.bazi['birth_date'].day,
            self.bazi['birth_date'].hour,
            self.bazi['birth_date'].minute
        )

    def analyze_career(self) -> Dict[str, Any]:
        """事业分析"""
        bazi = self.calculator.calculate()
        elements = self.calculator.get_element_balance()
        xingxiang = self.calculator.get_xingxiang()
        ten_gods = self.calculator.get_ten_gods()

        # 基础评分
        score = 60

        # 官杀星判断
        if '正官' in ten_gods.values() or '七杀' in ten_gods.values():
            score += 10

        # 印星判断
        if '正印' in ten_gods.values() or '偏印' in ten_gods.values():
            score += 5

        # 食伤判断
        if '食神' in ten_gods.values() or '伤官' in ten_gods.values():
            score += 5

        # 五行平衡
        element_values = list(elements.values())
        if max(element_values) - min(element_values) < 3:
            score += 10

        # 身强适合进取，身弱适合稳定
        if xingxiang == '身强':
            career_type = '适合创业或从事管理类工作，有较强的领导能力和执行力'
        else:
            career_type = '适合稳定型工作，如技术、财务、教育等，需要稳扎稳打'

        analysis = f"根据八字分析，您的事业格局为{xingxiang}。{career_type}。"

        # 添加建议
        suggestions = [
            "保持积极进取的心态，勇于把握机会",
            "加强专业技能培训，提升竞争力",
            "注意与上司和同事的关系处理",
            "可考虑合伙创业，但需谨慎选择搭档",
            "关注行业发展趋势，及时调整职业方向"
        ]

        return {
            'score': min(100, score),
            'analysis': analysis,
            'suggestions': suggestions[:5]
        }

    def analyze_wealth(self) -> Dict[str, Any]:
        """财运分析"""
        bazi = self.calculator.calculate()
        elements = self.calculator.get_element_balance()
        ten_gods = self.calculator.get_ten_gods()

        score = 60

        # 财星判断
        if '正财' in ten_gods.values():
            score += 15
        if '偏财' in ten_gods.values():
            score += 10

        # 身强能担财
        xingxiang = self.calculator.get_xingxiang()
        if xingxiang == '身强':
            score += 5

        # 食伤生财
        if '食神' in ten_gods.values() or '伤官' in ten_gods.values():
            score += 5

        # 财库
        day_branch = bazi['day']['branch']
        if day_branch in ['辰', '戌', '丑', '未']:
            score += 5

        wealth_type = '正财为主，偏财为辅' if '正财' in ten_gods.values() else '偏财为主，理财灵活'

        analysis = f"您的财运格局为{wealth_type}。整体财运平稳，但需注意理财方式。"

        suggestions = [
            "养成良好的储蓄习惯，避免冲动消费",
            "可适当进行稳健型投资，如基金、国债等",
            "注意守财，避免不必要的破财",
            "有条件可考虑房产等固定资产配置",
            "把握机遇，但需量力而行"
        ]

        return {
            'score': min(100, score),
            'analysis': analysis,
            'suggestions': suggestions[:5]
        }

    def analyze_love(self) -> Dict[str, Any]:
        """感情分析"""
        ten_gods = self.calculator.get_ten_gods()
        xingxiang = self.calculator.get_xingxiang()

        score = 60

        # 配偶星
        day_stem = self.calculator.get_day_master()
        if day_stem in ['甲', '庚']:
            score += 10  # 甲庚有正财
        if day_stem in ['乙', '辛']:
            score += 10

        # 桃花星
        day_branch = self.calculator.calculate()['day']['branch']
        if day_branch in ['申', '子', '辰', '酉']:
            score += 10

        # 身强感情丰富，身弱相对内敛
        if xingxiang == '身强':
            love_type = '主动热情，但需注意把握分寸'
        else:
            love_type = '相对内敛，需要时间来培养感情'

        analysis = f"您的感情运势：{love_type}。"

        suggestions = [
            "真诚对待感情，不要过于功利",
            "注意沟通方式和表达方法",
            "遇到合适的人要主动把握",
            "保持独立人格，不要过度依赖",
            "多方了解，不要急于确定关系"
        ]

        return {
            'score': min(100, score),
            'analysis': analysis,
            'suggestions': suggestions[:5]
        }

    def analyze_health(self) -> Dict[str, Any]:
        """健康分析"""
        bazi = self.calculator.calculate()
        elements = self.calculator.get_element_balance()
        xingxiang = self.calculator.get_xingxiang()

        score = 70

        # 找出最弱的五行
        min_element = min(elements, key=elements.get)

        # 身弱需注意
        if xingxiang == '身弱':
            score -= 5

        # 根据日支判断
        day_branch = bazi['day']['branch']
        health_notes = {
            '子': '注意泌尿系统',
            '丑': '注意脾胃',
            '寅': '注意肝胆',
            '卯': '注意肝脏',
            '辰': '注意脾胃',
            '巳': '注意心脏',
            '午': '注意心脏',
            '未': '注意脾胃',
            '申': '注意肺部',
            '酉': '注意肺部',
            '戌': '注意脾胃',
            '亥': '注意肾脏'
        }

        health_note = health_notes.get(day_branch, '注意身体健康')

        analysis = f"您的健康运势总体良好。需特别注意{health_note}方面的保养。"

        suggestions = [
            "保持规律作息，不要熬夜",
            "适度运动，增强体质",
            "注意饮食均衡",
            "定期体检，预防疾病",
            "保持心情愉悦，压力不要过大"
        ]

        return {
            'score': min(100, score),
            'analysis': analysis,
            'suggestions': suggestions[:5]
        }

    def analyze_personality(self) -> Dict[str, Any]:
        """性格分析"""
        elements = self.calculator.get_element_balance()
        xingxiang = self.calculator.get_xingxiang()

        score = 70

        # 五行性格
        day_stem = self.calculator.get_day_master()
        element = STEM_ELEMENT.get(day_stem, '')

        personalities = {
            '木': '正直仁慈，积极向上，有向上之心，但有时过于固执',
            '火': '热情开朗，积极主动，思维敏捷，但有时急躁',
            '土': '稳重厚道，为人诚实，脚踏实地，但有时保守',
            '金': '果断刚毅，有正义感，理财能力强，但有时固执',
            '水': '聪明智慧，灵活变通，适应性强的，但有时多变'
        }

        personality = personalities.get(element, '性格温和')

        if xingxiang == '身强':
            personality += '，且自信心较强'
        else:
            personality += '，且相对谦虚内敛'

        analysis = f"您的性格特点：{personality}"

        suggestions = [
            "发挥自身优势，完善性格短板",
            '学会控制情绪，避免冲动',
            '多与人沟通交流，扩大交际圈',
            '培养兴趣爱好，丰富生活',
            '保持学习心态，不断提升自我'
        ]

        return {
            'score': min(100, score),
            'analysis': analysis,
            'suggestions': suggestions[:5]
        }

    def analyze_all(self) -> Dict[str, Any]:
        """全面分析"""
        career = self.analyze_career()
        wealth = self.analyze_wealth()
        love = self.analyze_love()
        health = self.analyze_health()
        personality = self.analyze_personality()

        # 综合评分
        total_score = (career['score'] + wealth['score'] + love['score'] +
                      health['score'] + personality['score']) // 5

        return {
            'career': career,
            'wealth': wealth,
            'love': love,
            'health': health,
            'personality': personality,
            'overall_score': total_score,
            'bazi': self.calculator.calculate()
        }


# ============== 流年运势分析类 ==============

class LiunianAnalyzer:
    """流年运势分析类"""

    def __init__(self, bazi_data: Dict[str, Any], year: int = None):
        self.bazi = bazi_data
        self.year = year or datetime.now().year

    def get_liunian(self) -> Dict[str, Any]:
        """获取流年运势"""
        bazi = BaziCalculator(
            self.bazi['birth_date'].year,
            self.bazi['birth_date'].month,
            self.bazi['birth_date'].day,
            self.bazi['birth_date'].hour,
            self.bazi['birth_date'].minute
        ).calculate()

        # 流年天干地支
        year_ganzhi = LunarCalendar.get_ganzhi_year(self.year)

        # 大运（简化：直接从月柱开始推算）
        month_branch = bazi['month']['branch']
        dayun_start = self.bazi['birth_date'].year + 1

        score = 70

        # 根据流年五行判断
        year_stem = year_ganzhi[0]
        year_branch = year_ganzhi[1]

        year_element = STEM_ELEMENT.get(year_stem, '')
        branch_element = BRANCH_ELEMENT.get(year_branch, '')

        elements = BaziCalculator(
            self.bazi['birth_date'].year,
            self.bazi['birth_date'].month,
            self.bazi['birth_date'].day,
            self.bazi['birth_date'].hour,
            self.bazi['birth_date'].minute
        ).get_element_balance()

        # 生肖冲煞
        day_branch = bazi['day']['branch']
        conflicts = {
            '子': '午', '丑': '未', '寅': '申', '卯': '酉',
            '辰': '戌', '巳': '亥', '午': '子', '未': '丑',
            '申': '寅', '酉': '卯', '戌': '辰', '亥': '巳'
        }

        is_conflict = conflicts.get(day_branch) == year_branch

        if is_conflict:
            score -= 10

        analysis = f"{self.year}年流年运势：整体平稳，需注意顺应时势。"

        suggestions = [
            "保持积极心态，把握机遇",
            "注意人际关系处理",
            "健康方面需要多注意",
            "财务方面需谨慎",
            "多学习提升自我"
        ]

        return {
            'year': self.year,
            'ganzhi': year_ganzhi,
            'score': max(0, min(100, score)),
            'analysis': analysis,
            'suggestions': suggestions[:5],
            'is_conflict': is_conflict
        }


# ============== 合婚配对类 ==============

class MarriageAnalyzer:
    """合婚配对类"""

    @staticmethod
    def analyze(person1_bazi: Dict[str, Any], person2_bazi: Dict[str, Any]) -> Dict[str, Any]:
        """合婚分析"""
        bazi1 = BaziCalculator(
            person1_bazi['birth_date'].year,
            person1_bazi['birth_date'].month,
            person1_bazi['birth_date'].day,
            person1_bazi['birth_date'].hour,
            person1_bazi['birth_date'].minute
        ).calculate()

        bazi2 = BaziCalculator(
            person2_bazi['birth_date'].year,
            person2_bazi['birth_date'].month,
            person2_bazi['birth_date'].day,
            person2_bazi['birth_date'].hour,
            person2_bazi['birth_date'].minute
        ).calculate()

        score = 70

        # 日柱相合
        day1_stem = bazi1['day']['stem']
        day2_stem = bazi2['day']['stem']

        # 天干五合
        tianhe = {
            ('甲', '己'): 15, ('乙', '庚'): 15, ('丙', '辛'): 15,
            ('丁', '壬'): 15, ('戊', '癸'): 15
        }

        if (day1_stem, day2_stem) in tianhe or (day2_stem, day1_stem) in tianhe:
            score += 15

        # 地支三合
        day1_branch = bazi1['day']['branch']
        day2_branch = bazi2['day']['branch']

        sanhe_groups = [
            ('申', '子', '辰'), ('巳', '酉', '丑'), ('寅', '午', '戌'), ('亥', '卯', '未')
        ]

        for group in sanhe_groups:
            if day1_branch in group and day2_branch in group:
                score += 10
                break

        # 地支相冲
        conflicts = {
            ('子', '午'), ('丑', '未'), ('寅', '申'), ('卯', '酉'),
            ('辰', '戌'), ('巳', '亥')
        }

        if (day1_branch, day2_branch) in conflicts or (day2_branch, day1_branch) in conflicts:
            score -= 10

        # 年柱纳音
        score += 5  # 简化

        if score >= 85:
            level = '上等'
            desc = '两人八字非常合配，婚姻运势极佳'
        elif score >= 70:
            level = '中等'
            desc = '两人八字比较合配，婚姻运势良好'
        else:
            level = '下等'
            desc = '两人八字存在一些不合，需要相互包容'

        return {
            'score': max(0, min(100, score)),
            'level': level,
            'description': desc,
            'details': {
                'tiangan_he': '天干相合' if (day1_stem, day2_stem) in tianhe or (day2_stem, day1_stem) in tianhe else '天干不合',
                'dizhi_chong': '地支相冲' if (day1_branch, day2_branch) in conflicts or (day2_branch, day1_branch) in conflicts else '地支不冲'
            }
        }


# ============== 幸运要素类 ==============

class LuckyAnalyzer:
    """幸运要素分析类"""

    @staticmethod
    def get_lucky_color(bazi: Dict[str, Any]) -> Dict[str, Any]:
        """幸运颜色"""
        calculator = BaziCalculator(
            bazi['birth_date'].year,
            bazi['birth_date'].month,
            bazi['birth_date'].day,
            bazi['birth_date'].hour,
            bazi['birth_date'].minute
        )

        day_stem = calculator.get_day_master()
        element = STEM_ELEMENT.get(day_stem, '木')

        # 根据日主五行推荐颜色
        color_map = {
            '木': {'recommended': ['绿色', '青色'], 'avoid': ['白色', '金色']},
            '火': {'recommended': ['红色', '紫色'], 'avoid': ['黑色', '蓝色']},
            '土': {'recommended': ['黄色', '棕色'], 'avoid': ['绿色', '青色']},
            '金': {'recommended': ['白色', '金色'], 'avoid': ['红色', '紫色']},
            '水': {'recommended': ['黑色', '蓝色'], 'avoid': ['黄色', '棕色']}
        }

        colors = color_map.get(element, {'recommended': ['绿色'], 'avoid': ['红色']})

        return {
            'recommended': colors['recommended'],
            'avoid': colors['avoid'],
            'reason': f'您的日主为{element}，{colors["recommended"][0]}色最适合您'
        }

    @staticmethod
    def get_lucky_number(bazi: Dict[str, Any]) -> Dict[str, Any]:
        """幸运数字 - 根据日主确定"""
        calculator = BaziCalculator(
            bazi['birth_date'].year,
            bazi['birth_date'].month,
            bazi['birth_date'].day,
            bazi['birth_date'].hour,
            bazi['birth_date'].minute
        )

        day_stem = calculator.get_day_master()

        # 根据日主选择数字
        day_stem_elements = {
            '甲': '木', '乙': '木',
            '丙': '火', '丁': '火',
            '戊': '土', '己': '土',
            '庚': '金', '辛': '金',
            '壬': '水', '癸': '水'
        }

        element_numbers = {
            '木': [3, 8],
            '火': [2, 7],
            '土': [5, 10],
            '金': [4, 9],
            '水': [1, 6]
        }

        day_element = day_stem_elements.get(day_stem, '土')
        numbers = element_numbers.get(day_element, [5, 10])

        return {
            'lucky_numbers': numbers,
            'reason': f'您的日主是{day_stem}（{day_element}），数字{numbers[0]}和{numbers[1]}是您的幸运数字'
        }

    @staticmethod
    def get_lucky_direction(bazi: Dict[str, Any]) -> Dict[str, Any]:
        """幸运方位"""
        calculator = BaziCalculator(
            bazi['birth_date'].year,
            bazi['birth_date'].month,
            bazi['birth_date'].day,
            bazi['birth_date'].hour,
            bazi['birth_date'].minute
        )

        day_stem = calculator.get_day_master()

        # 根据日支确定吉利方位
        bazi_data = calculator.calculate()
        day_branch = bazi_data['day']['branch']

        direction_map = {
            '子': '北方', '丑': '东北方', '寅': '东北方', '卯': '东方',
            '辰': '东南方', '巳': '东南方', '午': '南方', '未': '西南方',
            '申': '西南方', '酉': '西方', '戌': '西北方', '亥': '西北方'
        }

        main_direction = direction_map.get(day_branch, '北方')

        return {
            'main_direction': main_direction,
            'good_directions': [main_direction],
            'avoid_directions': ['正南方'] if '南' not in main_direction else ['正北方']
        }


# ============== AI 解析类 ==============

class AIAnalyzer:
    """AI智能解析类"""

    def __init__(self):
        self.api_key = os.getenv('MINIMAX_API_KEY', '')
        self.model = os.getenv('LITELLM_MODEL', 'minimax/maxi-abel')
        self.api_base = os.getenv('MINIMAX_API_BASE', 'https://api.minimax.io/v1')

    def generate_analysis(self, bazi_data: Dict[str, Any], category: str) -> str:
        """使用AI生成详细分析"""
        if not self.api_key:
            return ""

        bazi = bazi_data['bazi']
        bazi_str = f"年柱: {bazi['year']['ganzhi']} ({bazi['year']['stem']}{bazi['year']['branch']})\n"
        bazi_str += f"月柱: {bazi['month']['ganzhi']} ({bazi['month']['stem']}{bazi['month']['branch']})\n"
        bazi_str += f"日柱: {bazi['day']['ganzhi']} ({bazi['day']['stem']}{bazi['day']['branch']})\n"
        bazi_str += f"时柱: {bazi['hour']['ganzhi']} ({bazi['hour']['stem']}{bazi['hour']['branch']})"

        prompts = {
            'career': f"""请根据以下八字分析事业运势，要求：
1. 总体评分（1-100）
2. 详细文字说明（300-500字）
3. 具体建议（3-5条）

八字信息：
{bazi_str}

请输出JSON格式：
{{"score": 分数, "analysis": "详细说明", "suggestions": ["建议1", "建议2", "建议3"]}}""",

            'wealth': f"""请根据以下八字分析财运运势，要求：
1. 总体评分（1-100）
2. 详细文字说明（300-500字）
3. 具体建议（3-5条）

八字信息：
{bazi_str}

请输出JSON格式：
{{"score": 分数, "analysis": "详细说明", "suggestions": ["建议1", "建议2", "建议3"]}}""",

            'love': f"""请根据以下八字分析感情运势，要求：
1. 总体评分（1-100）
2. 详细文字说明（300-500字）
3. 具体建议（3-5条）

八字信息：
{bazi_str}

请输出JSON格式：
{{"score": 分数, "analysis": "详细说明", "suggestions": ["建议1", "建议2", "建议3"]}}""",

            'health': f"""请根据以下八字分析健康运势，要求：
1. 总体评分（1-100）
2. 详细文字说明（300-500字）
3. 具体建议（3-5条）

八字信息：
{bazi_str}

请输出JSON格式：
{{"score": 分数, "analysis": "详细说明", "suggestions": ["建议1", "建议2", "建议3"]}}""",

            'personality': f"""请根据以下八字分析性格特点，要求：
1. 总体评分（1-100）
2. 详细文字说明（300-500字）
3. 具体建议（3-5条）

八字信息：
{bazi_str}

请输出JSON格式：
{{"score": 分数, "analysis": "详细说明", "suggestions": ["建议1", "建议2", "建议3"]}}"""
        }

        prompt = prompts.get(category, prompts['career'])

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model.replace('minimax/', ''),
                    'messages': [
                        {'role': 'system', 'content': '你是一位专业的命理分析师，擅长八字命理分析。请根据用户提供的八字信息进行分析，并按照要求的JSON格式输出结果。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.7
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']

        except Exception as e:
            print(f"AI分析请求失败: {e}")

        return ""


# ============== 数据库类 ==============

class Database:
    """MongoDB数据库类"""

    def __init__(self):
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        """连接数据库"""
        try:
            mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
            self.client = MongoClient(mongo_uri)
            self.db = self.client['bazi_app']
            print("数据库连接成功")
        except Exception as e:
            print(f"数据库连接失败: {e}")

    def save_user(self, user_data: Dict[str, Any]) -> str:
        """保存用户数据"""
        if self.db is not None:
            result = self.db.users.insert_one(user_data)
            return str(result.inserted_id)
        return ""

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """获取用户数据"""
        if self.db is not None:
            return self.db.users.find_one({'_id': user_id})
        return {}

    def get_user_by_bazi(self, bazi_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据八字获取用户"""
        if self.db is not None:
            return list(self.db.users.find(bazi_data))
        return []


# ============== 数据模型 ==============

class BaziRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    minute: int
    birthplace: Optional[str] = ""


class BaziResponse(BaseModel):
    bazi: Dict[str, Any]
    analysis: Dict[str, Any]
    lucky: Dict[str, Any]


class MarriageRequest(BaseModel):
    person1: BaziRequest
    person2: BaziRequest


# ============== FastAPI 应用 ==============

app = FastAPI(title="八字算命API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库实例
db = Database()
ai_analyzer = AIAnalyzer()


@app.get("/")
def root():
    return {"message": "八字算命API服务", "version": "1.0.0"}


@app.post("/bazi", response_model=BaziResponse)
def calculate_bazi(request: BaziRequest):
    """计算八字并分析"""
    # 创建八字计算器
    calculator = BaziCalculator(
        request.year, request.month, request.day,
        request.hour, request.minute, request.birthplace
    )

    bazi_data = calculator.calculate()

    # 命理分析
    analyzer = BaziAnalyzer({
        'birth_date': datetime(request.year, request.month, request.day, request.hour, request.minute),
        'birthplace': request.birthplace
    })

    analysis = analyzer.analyze_all()

    # 幸运要素
    lucky = {
        'color': LuckyAnalyzer.get_lucky_color({'birth_date': datetime(request.year, request.month, request.day, request.hour, request.minute)}),
        'number': LuckyAnalyzer.get_lucky_number({'birth_date': datetime(request.year, request.month, request.day, request.hour, request.minute)}),
        'direction': LuckyAnalyzer.get_lucky_direction({'birth_date': datetime(request.year, request.month, request.day, request.hour, request.minute)})
    }

    # 尝试AI增强
    try:
        ai_analysis = ai_analyzer.generate_analysis(
            {'bazi': bazi_data, 'birth_date': datetime(request.year, request.month, request.day, request.hour, request.minute)},
            'career'
        )
        if ai_analysis:
            # 解析AI返回的内容
            pass
    except:
        pass

    # 保存到数据库（可选，如果MongoDB未运行则跳过）
    try:
        user_data = {
            'bazi': bazi_data,
            'birth_date': datetime(request.year, request.month, request.day, request.hour, request.minute),
            'birthplace': request.birthplace,
            'created_at': datetime.now()
        }
        db.save_user(user_data)
    except Exception as e:
        print(f"数据库保存跳过: {e}")

    return {
        'bazi': bazi_data,
        'analysis': analysis,
        'lucky': lucky
    }


@app.get("/liunian/{year}")
def get_liunian(request: BaziRequest, year: int):
    """获取流年运势"""
    analyzer = LiunianAnalyzer({
        'birth_date': datetime(request.year, request.month, request.day, request.hour, request.minute),
        'birthplace': request.birthplace
    }, year)

    return analyzer.get_liunian()


@app.post("/marriage")
def analyze_marriage(request: MarriageRequest):
    """合婚配对分析"""
    person1_data = {
        'birth_date': datetime(request.person1.year, request.person1.month, request.person1.day,
                               request.person1.hour, request.person1.minute),
        'birthplace': request.person1.birthplace
    }
    person2_data = {
        'birth_date': datetime(request.person2.year, request.person2.month, request.person2.day,
                               request.person2.hour, request.person2.minute),
        'birthplace': request.person2.birthplace
    }

    result = MarriageAnalyzer.analyze(person1_data, person2_data)

    return result


@app.get("/daily")
def get_daily_luck(bazi: str):
    """每日运势"""
    # 简化实现
    today = datetime.now()
    day_of_year = today.timetuple().tm_yday

    luck_items = ['大吉', '吉', '平', '凶', '大凶']
    luck = luck_items[day_of_year % 5]

    return {
        'date': today.strftime('%Y-%m-%d'),
        'overall': luck,
        'career': luck_items[(day_of_year + 1) % 5],
        'love': luck_items[(day_of_year + 2) % 5],
        'wealth': luck_items[(day_of_year + 3) % 5],
        'health': luck_items[(day_of_year + 4) % 5]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)