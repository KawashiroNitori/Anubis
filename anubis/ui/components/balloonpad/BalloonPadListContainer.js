/**
 * Created by Nitori on 2017/3/26.
 */
import React from 'react';
import { connect } from 'react-redux';
import classNames from 'classnames';
import i18n from '../../utils/i18n';

import BalloonRow from './BalloonPadListItemContainer';

const mapStateToProps = (state, ownProps) => ({
    ...ownProps,
    isLoading: state.isLoading || state.isPosting,
});

@connect(mapStateToProps)
export default class BalloonPadListContainer extends React.PureComponent {
    render() {
        const cn = classNames('data-table balloonpad__table no-padding', {
            loading: this.props.isLoading,
        });
        return (
            <table className={cn}>
                <colgroup>
                    <col className="col--uname" />
                    <col className="col--nickname" />
                    <col className="col--letter" />
                    <col className="col--balloon" />
                </colgroup>
                <thead>
                    <tr>
                        <th className="col--uname">{i18n('User')}</th>
                        <th className="col--nickname">{i18n('Nickname')}</th>
                        <th className="col--letter">{i18n('Problem')}</th>
                        <th className="col--balloon">{i18n('Balloon')}</th>
                    </tr>
                </thead>
                <tbody>
                {this.props.list.map(item => (
                    <BalloonRow
                        key={`t${item.tid}u${item.uid}p${item.pid}`}
                        item={item}
                    />
                ))}
                </tbody>
            </table>
        );
    }
}
