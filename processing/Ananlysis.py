import numpy as np
from numba import njit
from config.Settings import TAX_RATE, RISK_FREE_RATE, BETA


class CashFlowModel:

    # Cache ค่า “แพง” (Senior move)
    def __init__(self, income_data, balance_data, cashflow_data):
        self.income_data = income_data
        self.balance_data = balance_data
        self.cashflow_data = cashflow_data

        # cache
        self._wacc = None

    # Cost of Equity (Vectorized + Stable)
    def cost_of_equity(self, market_return=None):
        mr = np.asarray(
            market_return if market_return is not None else
            [0.07, 0.08, 0.09, 0.10],
            dtype=float
        )
        market_premium = mr.mean() - RISK_FREE_RATE
        return RISK_FREE_RATE + BETA * market_premium

    # WACC (Cached)
    def wacc(self):
        if self._wacc is not None:
            return self._wacc

        equity = self.balance_data.get("Total Shareholder Equity", 0.0)
        debt = self.balance_data.get("Total Debt", 0.0)

        capital = equity + debt
        weights = np.array([equity, debt]) / capital

        interest = abs(self.cashflow_data.get("Interest Paid", 0.0))
        cost_of_debt = interest / debt if debt > 0 else 0.0

        costs = np.array([
            self.cost_of_equity(),
            cost_of_debt * (1 - TAX_RATE)
        ])

        self._wacc = np.dot(weights, costs)
        return self._wacc

    # Unlevered Free Cash Flow (UFCF)
    def unlevered_free_cash_flow(self):
        components = np.array([
            self.income_data["Operating Income"] * (1 - TAX_RATE),
            self.income_data["Depreciation and Amortization"],
            - self.cashflow_data["Capital Expenditure"],
            - self.cashflow_data["Change in Working Capital"]
        ], dtype=float)

        return components.sum()

    # Growth
    def growth_rate_cagr(self, start, end, years):
        return np.expm1(np.log(end / start) / years)
    
    # DCF Valuation
    def dcf_model_multiyear(self, ufcf_series):
        ufcf = np.asarray(ufcf_series, dtype=float)
        n = ufcf.size

        wacc = self.wacc()
        t = np.arange(1, n + 1)

        discount = np.exp(-np.log1p(wacc) * t)
        discounted_cf = ufcf * discount

        g = self.growth_rate_cagr(ufcf[0], ufcf[-1], n)
        terminal = (ufcf[-1] * (1 + g)) / (wacc - g)
        terminal_discounted = terminal * discount[-1]

        return discounted_cf.sum() + terminal_discounted

    # Intrinsic Value Per Share
    def intrinsic_value_per_share(self, ufcf_series):
        enterprise_value = self.dcf_model_multiyear(ufcf_series)
        shares = self.balance_data["Shares Outstanding"]
        return enterprise_value / shares

    # 💰 Cash Flow Metrics
    def Operating_Cash_Flow(self):
        components = np.array([
            self.income_data["Net Income", 0.0],
            self.income_data.get("Depreciation and Amortization", 0.0),
            self.cashflow_data.get("Stock Based Compensation", 0.0),
            self.cashflow_data.get("Other Non Cash Items", 0.0),
            self.cashflow_data["Change in Working Capital", 0.0]
        ])
        return components.sum()
    
    def Free_Cash_Flow(self):
        return self.Operating_Cash_Flow() - self.cashflow_data["Capital Expenditure", 0.0]
    
    #⚙️ Efficiency Ratios

    def asset_turnover(self):
        return np.divide(
            self.income_data.get("Revenue", 0.0),
            self.balance_data.get("Total Assets", 0.0),
            out=np.nan,
            where=self.balance_data.get("Total Assets", 0.0) > 0
        )

    def inventory_turnover(self):
        return np.divide(
            self.income_data.get("Cost of Goods Sold", 0.0),
            self.balance_data.get("Inventory", 0.0),
            out=np.nan,
            where=self.balance_data.get("Inventory", 0.0) > 0
        )


    def receivables_turnover(self):
        return np.divide(
            self.income_data.get("Revenue", 0.0),
            self.balance_data.get("Accounts Receivable", 0.0),
            out=np.nan,
            where=self.balance_data.get("Accounts Receivable", 0.0) > 0
            )


    def days_sales_outstanding(self):
        rt = self.receivables_turnover()
        return np.divide(365.0, rt, out=np.nan, where=rt > 0)
    

    def working_capital_turnover(self):
        working_capital = (
            self.balance_data.get("Total Current Assets", 0.0)
           - self.balance_data.get("Total Current Liabilities", 0.0)
        )
        return np.divide(
            self.income_data.get("Revenue", 0.0),
            working_capital,
            out=np.nan,
            where=working_capital != 0
    ) 

    #📈 Profitability Ratios
    def ROE(self):
        return np.divide(
            self.income_data.get("Net Income", 0.0),
            self.balance_data.get("Total Shareholder Equity", 0.0),
            out=np.nan,
            where=self.balance_data.get("Total Shareholder Equity", 0.0) > 0
        ) * 100


    def ROA(self):
        return np.divide(
            self.income_data.get("Net Income", 0.0),
            self.balance_data.get("Total Assets", 0.0),
            out=np.nan,
            where=self.balance_data.get("Total Assets", 0.0) > 0
        ) * 100


    def gross_profit_margin(self):
        return np.divide(
            self.income_data.get("Gross Profit", 0.0),
            self.income_data.get("Revenue", 0.0),
            out=np.nan,
            where=self.income_data.get("Revenue", 0.0) > 0
        ) * 100


    def operation_profit_margin(self):
        return np.divide(
            self.income_data.get("Operating Income", 0.0),
            self.income_data.get("Revenue", 0.0),
            out=np.nan,
            where=self.income_data.get("Revenue", 0.0) > 0
        ) * 100

    def net_profit_margin(self):
        return np.divide(
            self.income_data.get("Net Income", 0.0),
            self.income_data.get("Revenue", 0.0),
            out=np.nan,
            where=self.income_data.get("Revenue", 0.0) > 0
        ) * 100


    def ebitda_margin(self):
        return np.divide(
            self.income_data.get("EBITDA", 0.0),
            self.income_data.get("Revenue", 0.0),
            out=np.nan,
            where=self.income_data.get("Revenue", 0.0) > 0
        ) * 100

    #🧮 Valuation Metrics
    def Owners_Earnings(self):
        components = np.array([
            self.income_data.get("Net Income", 0.0),
            self.cashflow_data.get("Depreciation and Amortization", 0.0),
            - self.cashflow_data.get("Capital Expenditure", 0.0),
            - self.cashflow_data.get("Change in Working Capital", 0.0)
        ])
        return components.sum()


    def EPS_Ratio(self):
        return np.divide(
            self.income_data.get("Net Income", 0.0),
            self.income_data.get("Weighted Average Shares", 0.0),
            out=np.nan,
            where=self.income_data.get("Weighted Average Shares", 0.0) > 0
        )


    def PE_Ratio(self):
        return np.divide(
            self.income_data.get("price", 0.0),
            self.income_data.get("EPS", 0.0),
            out=np.nan,
            where=self.income_data.get("EPS", 0.0) > 0
        )


    def PB_Ratio(self):
        book_value_per_share = np.divide(
            self.balance_data.get("Total Shareholder Equity", 0.0),
            self.balance_data.get("Shares Outstanding", 0.0),
            out=np.nan,
            where=self.balance_data.get("Shares Outstanding", 0.0) > 0
        )
        return np.divide(
            self.income_data.get("price", 0.0),
            book_value_per_share,
            out=np.nan,
            where=book_value_per_share > 0
        )

    # 💧 Liquidity Ratios
    def current_ratio(self):
        return np.divide(
            self.balance_data.get("Total Current Assets", 0.0),
            self.balance_data.get("Total Current Liabilities", 0.0),
            out=np.nan,
            where=self.balance_data.get("Total Current Liabilities", 0.0) > 0
        )


    def quick_ratio(self):
        quick_assets = (
            self.balance_data.get("Total Current Assets", 0.0)
            - self.balance_data.get("Inventory", 0.0)
        )
        return np.divide(
            quick_assets,
            self.balance_data.get("Total Current Liabilities", 0.0),
            out=np.nan,
            where=self.balance_data.get("Total Current Liabilities", 0.0) > 0
        )


    def cash_ratio(self):
        cash_assets = (
            self.balance_data.get("Cash and Cash Equivalents", 0.0)
            + self.balance_data.get("Short Term Investments", 0.0)
        )
        return np.divide(
            cash_assets,
            self.balance_data.get("Total Current Liabilities", 0.0),
            out=np.nan,
            where=self.balance_data.get("Total Current Liabilities", 0.0) > 0
        )


"""
    def inventory_turnover(income_data, balance_data):
        return income_data["Cost of Goods Sold"] / balance_data["Inventory"]


    def receivables_turnover(income_data, balance_data):
        return income_data["Revenue"] / balance_data["Accounts Receivable"]


    def days_sales_outstanding(income_data, balance_data):
        return 365 / receivables_turnover(income_data, balance_data)


    def working_capital_turnover(income_data, balance_data):
        working_capital = (
            balance_data["Total Current Assets"]
            - balance_data["Total Current Liabilities"]
        )
        return income_data["Revenue"] / working_capital

    #📈 Profitability Ratios

    def ROE(income_data, balance_data):
        return (income_data["Net Income"] / balance_data["Total Shareholder Equity"]) * 100


    def ROA(income_data, balance_data):
        return (income_data["Net Income"] / balance_data["Total Assets"]) * 100


    def gross_profit_margin(income_data):
        return (income_data["Gross Profit"] / income_data["Revenue"]) * 100


    def operation_profit_margin(income_data):
        return (income_data["Operating Income"] / income_data["Revenue"]) * 100


    def net_profit_margin(income_data):
        return (income_data["Net Income"] / income_data["Revenue"]) * 100


    def ebitda_margin(income_data):
        return (income_data["EBITDA"] / income_data["Revenue"]) * 100

    #🧮 Valuation Metrics
    def Owners_Earnings(income_data, cashflow_data):
        components = np.array([
            income_data["Net Income"],
            cashflow_data["Depreciation and Amortization"],
            -cashflow_data["Capital Expenditure"],
            -cashflow_data["Change in Working Capital"]
        ])
        return components.sum()


    def EPS_Ratio(income_data):
        return income_data["Net Income"] / income_data["Weighted Average Shares"]


    def PE_Ratio(income_data):
        return income_data["price"] / income_data["EPS"]


    def PB_Ratio(income_data, balance_data):
        book_value_per_share = (
            balance_data["Total Shareholder Equity"]
            / balance_data["Shares Outstanding"]
        )
        return income_data["price"] / book_value_per_share

    # 💧 Liquidity Ratios
    def current_ratio(balance_data):
        return (
            balance_data["Total Current Assets"]
            / balance_data["Total Current Liabilities"]
        )


    def quick_ratio(balance_data):
        return (
            (balance_data["Total Current Assets"] - balance_data["Inventory"])
            / balance_data["Total Current Liabilities"]
        )


    def cash_ratio(balance_data):
        return (
            balance_data["Cash and Cash Equivalents"]
            + balance_data["Short Term Investments"]
        )   / balance_data["Total Current Liabilities"]








    #1️⃣ Core DCF Engine (Vectorized + Stable)
    @njit(fastmath=True)
    def dcf_value(ufcf, wacc, g):
        n = ufcf.shape[0]
        t = np.arange(1, n + 1)

        discount = np.exp(-np.log1p(wacc) * t)
        pv_cf = np.sum(ufcf * discount)

        terminal = (ufcf[-1] * (1 + g)) / (wacc - g)
        terminal_pv = terminal * discount[-1]

        return pv_cf + terminal_pv

    # 2️⃣ Monte Carlo DCF (แจกแจง WACC / Growth)
    def monte_carlo_dcf(
        ufcf,
        shares,
        wacc_mean,
        wacc_std,
        g_mean,
        g_std,
        simulations=10000
    ):
        wacc_samples = np.random.normal(wacc_mean, wacc_std, simulations)
        g_samples = np.random.normal(g_mean, g_std, simulations)

        values = np.zeros(simulations)

        for i in range(simulations):
            if wacc_samples[i] <= g_samples[i]:
                values[i] = np.nan
            else:
                values[i] = dcf_value(ufcf, wacc_samples[i], g_samples[i]) / shares

        return {
            "mean": np.nanmean(values),
            "median": np.nanmedian(values),
            "p10": np.nanpercentile(values, 10),
            "p50": np.nanpercentile(values, 50),
            "p90": np.nanpercentile(values, 90),
            "distribution": values
        }
    
    #3️⃣ Scenario Matrix (Bull / Base / Bear)

    def scenario_matrix_dcf(
        ufcf,
        shares,
        base_wacc,
        base_growth
    ):
        scenarios = {
            "Bear": (base_wacc + 0.02, base_growth - 0.02),
            "Base": (base_wacc, base_growth),
            "Bull": (base_wacc - 0.02, base_growth + 0.02),
        }

        result = {}
        for name, (wacc, g) in scenarios.items():
            if wacc <= g:
                result[name] = None
            else:
                result[name] = dcf_value(ufcf, wacc, g) / shares

        return result
"""