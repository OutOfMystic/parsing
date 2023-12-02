

class MarginRules:
    def __init__(self, id_, name, rules):
        self.id = id_
        self.name = name
        self.rules = rules

    def __call__(self, price: int):
        type_, value = self._get_rule(price)
        if type_ == 'equal':
            return int(value)
        elif type_ == 'plus':
            return (price + int(value)) // 100 * 100
        elif type_ == 'coef':
            return int(price * value) // 100 * 100
        else:
            AssertionError(f'Margin rule is wrong: {type_}')

    def _get_rule(self, price):
        for min_val, max_val, type_, value in self.rules:
            if price in range(min_val, max_val):
                return type_, value
        else:
            _, _, type_, value = self.rules[-1]
            return type_, value
