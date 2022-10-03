

class MarginRules:
    def __init__(self, rules):
        self.rules = rules

    def __call__(self, price: int):
        if not isinstance(price, int):
            raise ValueError(f'Price should be integer, not {type(price).__name__}')
        type_, value = self._get_rule(price)
        if type_ == 'equal':
            return value
        elif type_ == 'plus':
            return price + value
        elif type_ == 'coef':
            return int(price)
        else:
            AssertionError(f'Margin rule is wrong: {type_}')

    def _get_rule(self, price):
        for min_val, max_val, type_, value in self.rules:
            if not ((price >= min_val) and (price <= max_val)):
                continue
            return type_, value
        else:
            return self.rules[-1][2:]